"""
Multi-monitor screenshot helper.

The tricky part is keeping THREE coordinate systems straight:

  1. PHYSICAL  — what mss.grab() returns. Real GPU pixels. e.g. 2560x1440.
  2. LOGICAL   — what the OS / Qt cursor uses after DPI scaling. e.g. 1707x960
                 on a 150%-DPI 2560x1440 display.
  3. DOWNSCALED — what we send to the LLM (1280-wide JPEG to keep tokens low).

The overlay plots in LOGICAL coordinates. The element-detector model sees the
downscaled image. So `detect_element` must return coords in LOGICAL space, with
the monitor's logical-origin offset applied for multi-monitor setups.

ScreenShot now carries every number needed to convert between them.
"""

import base64
import io
import os
import sys
from dataclasses import dataclass
from typing import List

import mss
import mss.tools
from PIL import Image


@dataclass
class ScreenShot:
    index: int

    # Downscaled image actually sent to the LLM
    width: int            # downscaled width (pixels in JPEG)
    height: int           # downscaled height
    base64_jpeg: str

    # Real (physical) monitor size and origin in mss virtual-screen coords
    physical_width: int
    physical_height: int
    physical_left: int    # mss-reported origin (physical px)
    physical_top: int

    # DPI scale (physical / logical). 1.0 on normal displays, 1.5 on 150% DPI.
    dpi_scale: float

    # Convenience: where this monitor's top-left sits in LOGICAL screen space
    logical_left: int
    logical_top: int


def _query_dpi_scale() -> float:
    """Best-effort DPI scale for the primary monitor.
    Returns 1.0 if anything goes wrong."""
    if sys.platform == "win32":
        try:
            import ctypes
            u = ctypes.windll.user32
            u.SetProcessDPIAware()
            gdfs = getattr(u, "GetDpiForSystem", None)
            if gdfs:
                return max(1.0, gdfs() / 96.0)
        except Exception:
            pass
    else:
        for var in ("GDK_SCALE", "QT_SCALE_FACTOR"):
            try:
                v = os.environ.get(var)
                if v:
                    return max(1.0, float(v))
            except (ValueError, TypeError):
                pass
        try:
            import subprocess
            out = subprocess.check_output(
                ["xrdb", "-query"], stderr=subprocess.DEVNULL, text=True, timeout=2
            )
            for line in out.splitlines():
                if "Xft.dpi" in line:
                    dpi = float(line.split(":")[-1].strip())
                    return max(1.0, dpi / 96.0)
        except Exception:
            pass
    return 1.0


def _encode(img: Image.Image, max_width: int):
    """Downscale (for the LLM) and JPEG/base64 encode; returns (img, b64)."""
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75, optimize=True)
    return img, base64.b64encode(buf.getvalue()).decode("utf-8")


def _is_blank(img: Image.Image) -> bool:
    """True for an all-black frame — what mss returns on Wayland."""
    try:
        return not any(hi for _lo, hi in img.convert("RGB").getextrema())
    except Exception:
        return False


def _capture_via_gnome(max_width: int) -> List[ScreenShot]:
    """Capture through the GNOME extension (works on Wayland). [] if unavailable."""
    from screen import gnome_bridge
    if not gnome_bridge.available():
        return []
    info = gnome_bridge.screenshot()
    if not info:
        return []
    path = info["path"]
    try:
        full = Image.open(path)
        full.load()
    except Exception:
        return []
    finally:
        gnome_bridge._unlink(path)
    stage_w = max(1, int(info["stage"]["w"]))
    scale = full.width / stage_w                      # physical px per logical px
    gnome_bridge.last_scale = scale
    mons = sorted(info.get("monitors") or [], key=lambda m: not m.get("primary"))
    if not mons:
        mons = [{"x": 0, "y": 0, "w": stage_w, "h": int(info["stage"]["h"])}]
    results = []
    for i, m in enumerate(mons, start=1):
        box = (int(m["x"] * scale), int(m["y"] * scale),
               int((m["x"] + m["w"]) * scale), int((m["y"] + m["h"]) * scale))
        crop = full.crop(box)
        if _is_blank(crop):
            continue
        img, enc = _encode(crop, max_width)
        results.append(ScreenShot(
            index=i, width=img.width, height=img.height, base64_jpeg=enc,
            physical_width=crop.width, physical_height=crop.height,
            physical_left=box[0], physical_top=box[1], dpi_scale=scale,
            logical_left=int(m["x"]), logical_top=int(m["y"]),
        ))
    return results


def capture_all_screens(max_width: int = 1280) -> List[ScreenShot]:
    """Capture all monitors. Each ScreenShot carries everything needed
    to convert detection coords back into logical screen space.

    Returns [] when the screen cannot be captured (e.g. a blank frame on Wayland
    without the GNOME extension) so callers say "I can't see your screen" instead
    of sending a black image to a model that then guesses."""
    if sys.platform.startswith("linux"):
        via = _capture_via_gnome(max_width)
        if via:
            return via
    dpi = _query_dpi_scale()
    results = []
    with mss.mss() as sct:
        # mss monitor index 0 is the combined virtual screen; 1+ are real monitors
        for i, monitor in enumerate(sct.monitors[1:], start=1):
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            if _is_blank(img):
                _warn_blank_once()
                continue

            phys_w, phys_h = img.width, img.height
            phys_left = int(monitor.get("left", 0))
            phys_top  = int(monitor.get("top",  0))

            # Downscale only the JPEG we send to the LLM — keep physical numbers intact
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize(
                    (max_width, int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")

            results.append(ScreenShot(
                index=i,
                width=img.width,
                height=img.height,
                base64_jpeg=encoded,
                physical_width=phys_w,
                physical_height=phys_h,
                physical_left=phys_left,
                physical_top=phys_top,
                dpi_scale=dpi,
                logical_left=int(round(phys_left / dpi)),
                logical_top=int(round(phys_top  / dpi)),
            ))

    return results


def no_screen_message() -> str:
    """What to say when a capture is impossible, with the real reason when known."""
    try:
        from screen import gnome_bridge
        if sys.platform.startswith("linux") and gnome_bridge.outdated():
            return ("I need one more step to see your screen: log out and back in once "
                    "so the updated Glance extension loads.")
    except Exception:
        pass
    return "I can't see your screen right now."


_warned_blank = False


def _warn_blank_once() -> None:
    global _warned_blank
    if not _warned_blank:
        _warned_blank = True
        print("[glance] screen capture returned a blank frame (Wayland?). "
              "Install/enable the Glance Cursor GNOME extension and log in again.",
              flush=True)


def capture_primary() -> ScreenShot:
    """Capture only the primary monitor."""
    screens = capture_all_screens()
    return screens[0] if screens else None


def screen_count() -> int:
    with mss.mss() as sct:
        return len(sct.monitors) - 1  # subtract virtual combined monitor
