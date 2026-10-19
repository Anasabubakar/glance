import io
import asyncio
from typing import Optional

from audio.stt.base_stt import BaseSTT
from audio.capture import pcm16_to_wav
from config import cfg

_model_cache = None


def _get_model():
    global _model_cache
    if _model_cache is None:
        from faster_whisper import WhisperModel
        # compute_type="int8" runs on CPU without CUDA; use "float16" if GPU available
        _model_cache = WhisperModel(cfg.whisper_model, device="cpu", compute_type="int8")
    return _model_cache


_PROMPT = ("Glance. Tile this window left. Minimize the terminal. Open the calculator. "
           "Set a timer for five minutes. Volume up. Copy that. Create a routine called morning.")


class FasterWhisperSTT(BaseSTT):
    """
    Local, offline speech-to-text using faster-whisper.
    No API key required. Runs entirely on CPU.
    Model is loaded once and cached.
    """

    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        wav_bytes = pcm16_to_wav(pcm_bytes, sample_rate)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, wav_bytes)

    def _run(self, wav_bytes: bytes) -> str:
        import tempfile, os
        model = _get_model()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            path = f.name
        try:
            # A short, in-domain prompt makes "Glance, tile this window left" come out right
            # instead of "Glans, tail the window laughed". It is dropped if it gets echoed.
            segments, _ = model.transcribe(
                path, beam_size=5, language="en", initial_prompt=_PROMPT,
                condition_on_previous_text=False, temperature=0.0, no_speech_threshold=0.5)
            kept = []
            for s in segments:
                if (s.no_speech_prob > 0.6 and s.avg_logprob < -0.7) or s.avg_logprob < -1.4:
                    continue
                kept.append(s.text.strip())
            text = " ".join(kept).strip()
            from audio.ambient_listener import collapse_repeats
            text = collapse_repeats(text)
            if text.lower().strip(" .") in _PROMPT.lower():       # it just repeated the prompt
                return ""
            return text
        finally:
            os.unlink(path)
