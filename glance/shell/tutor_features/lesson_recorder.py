"""
Lesson recording.

Captures Glance lessons as:
  • MP4 video — primary monitor, 8 fps, Glance's pointer overlaid
  • Markdown transcript — Q&A + timestamps next to the video

Output:  ~/Documents/Glance Lessons/<timestamp>/

Backend: imageio-ffmpeg (auto-bundles ffmpeg, no system install needed).
"""

from __future__ import annotations

import io
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image


FPS = 6


class LessonRecorder:
    """Headless screen recorder. Markdown transcript built up alongside."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._writer = None
        self._md_lines: list[str] = []
        self._t0: float = 0.0
        self._out_dir: Optional[Path] = None
        self.is_recording = False

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> Optional[Path]:
        """Begin recording. Returns the output directory or None on failure."""
        if self.is_recording:
            return self._out_dir

        first = self._grab()          # also proves the screen can be captured (not black)
        if first is None:
            return None
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._out_dir = Path.home() / "Documents" / "Glance Lessons" / ts
        self._out_dir.mkdir(parents=True, exist_ok=True)
        self._size = (first.size[0] // 2 * 2, first.size[1] // 2 * 2)     # even sizes for h264
        self._writer = _make_sink(self._out_dir, self._size)
        self._md_lines = [f"# Glance Lesson — {ts}", ""]
        self._t0 = time.monotonic()
        self._stop_evt.clear()
        self.is_recording = True

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self._out_dir

    def stop(self) -> Optional[Path]:
        """Stop and flush. Returns the output directory."""
        if not self.is_recording:
            return None
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None
        if self._out_dir:
            (self._out_dir / "transcript.md").write_text(
                "\n".join(self._md_lines), encoding="utf-8"
            )
        self.is_recording = False
        return self._out_dir

    # ── Transcript hooks (manager calls these) ──────────────────────────────

    def log_question(self, q: str):
        if self.is_recording:
            t = time.monotonic() - self._t0
            self._md_lines.append(f"\n## [{t:6.1f}s] Q: {q}\n")

    def log_answer(self, a: str):
        if self.is_recording:
            self._md_lines.append(f"**A:** {a.strip()}\n")

    # ── Internal ────────────────────────────────────────────────────────────

    def _grab(self):
        """One frame as a PIL image. Goes through Glance's screen capture, so it works on
        GNOME/Wayland (via the extension) as well as X11 and Windows. None if blank."""
        try:
            import base64
            from screen.capture import capture_all_screens
            shots = capture_all_screens(max_width=1600)
            if not shots:
                return None
            img = Image.open(io.BytesIO(base64.b64decode(shots[0].base64_jpeg))).convert("RGB")
            size = getattr(self, "_size", None)
            return img.resize(size) if size and img.size != size else img
        except Exception:
            return None

    def _loop(self):
        interval = 1.0 / FPS
        next_t = time.monotonic()
        while not self._stop_evt.is_set():
            img = self._grab()
            if img is not None and self._writer is not None:
                try:
                    self._writer.write(img)
                except Exception:
                    pass
            next_t += interval
            sleep_left = next_t - time.monotonic()
            if sleep_left > 0:
                time.sleep(sleep_left)
            else:
                next_t = time.monotonic()


class _FfmpegSink:
    """Pipes raw frames into the system ffmpeg: a real MP4, no Python video libraries."""

    def __init__(self, out_dir: Path, size, exe: str):
        import subprocess
        self.path = out_dir / "lesson.mp4"
        self._size = size
        self._p = subprocess.Popen(
            [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{size[0]}x{size[1]}", "-r", str(FPS), "-i", "-",
             "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(self.path)],
            stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def write(self, img: Image.Image):
        if img.size != self._size:
            img = img.resize(self._size)
        self._p.stdin.write(img.tobytes())

    def close(self):
        try:
            self._p.stdin.close()
            self._p.wait(timeout=20)
        except Exception:
            self._p.kill()


class _GifSink:
    """No ffmpeg on this computer: keep frames and save one animated GIF at the end."""

    def __init__(self, out_dir: Path, size):
        self.path = out_dir / "lesson.gif"
        self._frames: list = []
        w = min(size[0], 960)
        self._size = (w, int(size[1] * w / size[0]))

    def write(self, img: Image.Image):
        if len(self._frames) < 600:                        # about 100 s at 6 fps
            self._frames.append(img.resize(self._size).convert("P", palette=Image.Palette.ADAPTIVE))

    def close(self):
        if self._frames:
            self._frames[0].save(self.path, save_all=True, append_images=self._frames[1:],
                                 duration=int(1000 / FPS), loop=0, optimize=False)
            self._frames = []


def _make_sink(out_dir: Path, size):
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        try:
            return _FfmpegSink(out_dir, size, exe)
        except Exception:
            pass
    return _GifSink(out_dir, size)
