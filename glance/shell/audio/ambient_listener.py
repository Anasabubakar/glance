"""
Always-on ambient audio listener.
Handles:
  - Continuous mic stream (single sounddevice input)
  - Energy-based VAD to detect speech segments
  - Wake-word detection via faster-whisper tiny model (triggers on "glance" / "hey glance")
  - Push-to-talk buffering when hotkey is held
  - Streams RMS level to UI (cursor waveform + panel)
"""

import threading
import time
from enum import Enum, auto
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from audio.capture import pcm16_to_wav, SAMPLE_RATE


def _log(cat: str, msg: str) -> None:
    try:
        from session_log import slog
        slog(cat, msg)
    except Exception:
        print(f"[{cat}] {msg}", flush=True)


class Mode(Enum):
    STANDBY       = auto()   # wake-word scanning
    RECORDING     = auto()   # actively buffering user utterance


# ── Tuning knobs ──────────────────────────────────────────────────────────────
BLOCK_MS           = 30              # mic callback granularity
FRAMES_PER_BLOCK   = int(SAMPLE_RATE * BLOCK_MS / 1000)
ENERGY_THRESHOLD   = 0.006           # lower = catches quieter speech
MIN_SPEECH_BLOCKS  = 3               # ~90ms of speech to start a segment
SILENCE_BLOCKS_END = 20              # ~600ms of silence ends a segment
MAX_SEGMENT_BLOCKS = 120             # ~3.6s max wake-word segment
PRE_ROLL_BLOCKS    = 18              # ~540ms of pre-roll for the wake word

# Wake phrases — "glance" isn't a dictionary word, so whisper tiny mangles it a
# dozen ways; we cover the likely variants (and the "hey ___" forms).
WAKE_WORDS = (
    "glance", "clackie", "clacki", "clackey", "clacke", "clack e",
    "clack he", "clack a", "klacky", "klacki", "cracky", "clarky",
    "clark he", "clark e",
    "hey glance", "hi glance", "hey clack", "ok glance", "yo glance",
    "hey clackie", "hey clacki", "hey klacky", "hey cracky", "hey clarky",
)


def _skeleton(word: str) -> str:
    """Rough consonant skeleton so sound-alikes compare equal: g/c/q/k -> k,
    x -> ks, z -> s, vowels dropped. 'glance' -> 'klnk', 'k-lax' -> 'klks'."""
    out = []
    for ch in word:
        if ch in "gcqk":
            out.append("k")
        elif ch == "x":
            out.append("ks")
        elif ch in "zs":
            out.append("s")
        elif ch.isalpha() and ch not in "aeiouyhw":
            out.append(ch)
    return "".join(out)


def wake_match(text: str) -> bool:
    """True if `text` (a whisper transcript) contains the wake word. Whisper-tiny
    mangles 'Glance' a dozen ways, so besides the explicit phrases we accept
    near spellings (glans, clance) and sound-alikes that start gl/cl/kl (k-lax)."""
    import re
    from difflib import SequenceMatcher
    t = " ".join(re.sub(r"[^a-z]+", " ", text.lower()).split())
    if not t:
        return False
    if any(w in t for w in WAKE_WORDS):
        return True
    words = t.split()
    cands = words + [a + b for a, b in zip(words, words[1:])]   # also "k lax" -> "klax"
    target_sk = _skeleton("glance")
    for w in cands:
        if not (3 <= len(w) <= 8):
            continue
        if SequenceMatcher(None, w, "glance").ratio() >= 0.72:
            return True
        if w[0] in "gck" and w[1:2] in ("l", "") and \
                SequenceMatcher(None, _skeleton(w), target_sk).ratio() >= 0.74:
            return True
    return False


class AmbientListener:
    """
    Single sounddevice input stream with three outputs:
      1. level callback (always): drives cursor/panel waveform
      2. wake-word callback (standby): transcribes VAD segments with tiny whisper
      3. recording buffer (recording): full PCM buffer returned on stop_recording()
    """

    def __init__(
        self,
        on_level: Callable[[float], None],
        on_wake: Callable[[], None],
    ):
        self._on_level = on_level
        self._on_wake = on_wake

        self._mode: Mode = Mode.STANDBY
        self._stream: Optional[sd.InputStream] = None
        self._running = False

        # Rolling pre-roll ring buffer (small)
        self._preroll: list[np.ndarray] = []
        # Current speech segment buffer (for wake-word transcription)
        self._seg_buffer: list[np.ndarray] = []
        self._seg_speech_blocks = 0
        self._seg_silence_blocks = 0
        self._in_segment = False
        # Adaptive noise floor so steady room noise isn't mistaken for speech
        # (which made the wake check run every 3 s and burn CPU).
        self._noise_floor = 0.004

        # Recording buffer (hotkey push-to-talk OR post-wake capture)
        self._rec_buffer: list[bytes] = []
        # Optional live sink for streaming STT: called with each PCM chunk during
        # RECORDING (in addition to buffering). Set/cleared by the manager.
        self._on_rec_chunk = None

        # Lazy tiny whisper for wake word
        self._wake_model = None
        self._wake_lock = threading.Lock()
        self._wake_inflight = False

        # Enable/disable toggle (GLANCE_WAKE_WORD=0 starts disabled — e.g. demo
        # recording, where narration says "Glance" while she's idle)
        import os as _os
        self._wake_word_enabled = _os.environ.get("GLANCE_WAKE_WORD", "1") != "0"

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAMES_PER_BLOCK,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def start_recording(self) -> None:
        """Switch to RECORDING mode; all audio buffered for STT."""
        self._rec_buffer = []
        self._mode = Mode.RECORDING

    def stop_recording(self) -> bytes:
        """Return buffered PCM16 bytes and resume standby."""
        pcm = b"".join(self._rec_buffer)
        self._rec_buffer = []
        self._mode = Mode.STANDBY
        self._reset_segment()
        return pcm

    def set_rec_chunk_callback(self, cb) -> None:
        """Set (or clear with None) a sink called with each PCM chunk while
        RECORDING — used to stream audio to live STT."""
        self._on_rec_chunk = cb

    def set_wake_word_enabled(self, enabled: bool):
        self._wake_word_enabled = enabled

    @property
    def wake_word_enabled(self) -> bool:
        return self._wake_word_enabled

    # ── Audio callback ────────────────────────────────────────────────────────

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if not self._running:
            return

        pcm_int16 = indata[:, 0] if indata.ndim == 2 else indata
        pcm_float = pcm_int16.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(pcm_float ** 2)))
        self._on_level(rms)

        if self._mode == Mode.RECORDING:
            raw = pcm_int16.tobytes()
            self._rec_buffer.append(raw)
            cb = self._on_rec_chunk
            if cb is not None:
                try:
                    cb(raw)                    # stream to live STT (never crash here)
                except Exception:
                    pass
            return

        # Standby: VAD-based segment capture for wake-word
        if not self._wake_word_enabled:
            return

        # Maintain tiny pre-roll
        self._preroll.append(pcm_int16.copy())
        if len(self._preroll) > PRE_ROLL_BLOCKS:
            self._preroll.pop(0)

        if rms < self._noise_floor * 1.5:
            self._noise_floor = 0.98 * self._noise_floor + 0.02 * rms
        else:
            self._noise_floor *= 1.0004        # allow slow upward drift (new noise)
        is_speech = rms > max(ENERGY_THRESHOLD, self._noise_floor * 2.2)

        if not self._in_segment:
            if is_speech:
                self._seg_speech_blocks += 1
                self._seg_buffer.append(pcm_int16.copy())
                if self._seg_speech_blocks >= MIN_SPEECH_BLOCKS:
                    self._in_segment = True
                    # Prepend pre-roll so we catch the start of the word
                    self._seg_buffer = list(self._preroll) + self._seg_buffer
            else:
                self._seg_speech_blocks = max(0, self._seg_speech_blocks - 1)
                if not self._seg_speech_blocks:
                    self._seg_buffer = []
            return

        # In-segment
        self._seg_buffer.append(pcm_int16.copy())
        if is_speech:
            self._seg_silence_blocks = 0
        else:
            self._seg_silence_blocks += 1

        end = (
            self._seg_silence_blocks >= SILENCE_BLOCKS_END
            or len(self._seg_buffer) >= MAX_SEGMENT_BLOCKS
        )
        if end:
            seg = np.concatenate(self._seg_buffer).astype(np.int16).tobytes()
            self._reset_segment()
            self._dispatch_wake_check(seg)

    def _reset_segment(self):
        self._seg_buffer = []
        self._seg_speech_blocks = 0
        self._seg_silence_blocks = 0
        self._in_segment = False

    # ── Wake-word transcription (off the audio thread) ────────────────────────

    def _dispatch_wake_check(self, pcm: bytes):
        if self._wake_inflight:
            return
        self._wake_inflight = True
        t = threading.Thread(target=self._check_wake, args=(pcm,), daemon=True)
        t.start()

    def _check_wake(self, pcm: bytes):
        try:
            text = self._transcribe_tiny(pcm).lower().strip()
            if not text:
                return
            hit = wake_match(text)
            _log("WAKE", f"heard {text!r} -> {'MATCH' if hit else 'no match'}")
            if hit:
                self._on_wake()
        except Exception as e:
            _log("WAKE", f"wake check failed: {type(e).__name__}: {e}")
        finally:
            self._wake_inflight = False

    def _transcribe_tiny(self, pcm: bytes) -> str:
        """Pad PCM with silence (whisper accuracy degrades on ultra-short clips)."""
        import tempfile, os
        model = self._get_model()
        pad = bytes(int(SAMPLE_RATE * 0.4) * 2)    # 400ms silence each side
        padded = pad + pcm + pad
        wav = pcm16_to_wav(padded)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            path = f.name
        try:
            segments, _ = model.transcribe(
                path,
                beam_size=5,
                language="en",
                condition_on_previous_text=False,
                no_speech_threshold=0.45,
                temperature=0.0,
            )
            kept = []
            for seg in segments:
                # Whisper invents text over noise ("thanks for watching"); keep only
                # segments it is reasonably sure contain speech.
                if (seg.no_speech_prob > 0.6 and seg.avg_logprob < -0.7) or seg.avg_logprob < -1.3:
                    continue
                kept.append(seg.text)
            return " ".join(kept)
        finally:
            os.unlink(path)

    def _get_model(self):
        with self._wake_lock:
            if self._wake_model is None:
                from faster_whisper import WhisperModel
                self._wake_model = WhisperModel(
                    "tiny.en", device="cpu", compute_type="int8"
                )
            return self._wake_model
