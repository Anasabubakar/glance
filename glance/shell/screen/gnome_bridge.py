"""
Screen capture and input injection through the Glance Cursor GNOME extension.

On GNOME/Wayland an ordinary app can neither capture other windows (mss returns
a black image) nor click/type into them (pynput/xdotool only reach X11 apps).
The extension runs inside the compositor and can do both, over D-Bus
(app.glance.Overlay). This module is a thin, dependency-free client that shells
out to `gdbus` so it is safe to call from any thread.
"""

import ast
import json
import os
import subprocess
import tempfile
import time
from typing import Optional

SERVICE = "app.glance.Overlay"
PATH = "/app/glance/Overlay"

# physical px / logical px of the most recent capture; the actuator divides by this
# because the model's coordinates are mapped to physical pixels but the compositor
# takes logical stage coordinates.
last_scale: float = 1.0

_avail_cache = (0.0, False)


def _q(s: str) -> str:
    """GVariant-text string literal."""
    return "'" + (s.replace("\\", "\\\\").replace("'", "\\'")
                   .replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")) + "'"


def _call(method: str, *args: str, timeout: float = 10.0) -> Optional[str]:
    cmd = ["gdbus", "call", "--session", "--dest", SERVICE, "--object-path", PATH,
           "--method", f"{SERVICE}.{method}", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def available() -> bool:
    """True when the extension is loaded in this session (cached for 5 s)."""
    global _avail_cache
    now = time.monotonic()
    if now - _avail_cache[0] < 5.0:
        return _avail_cache[1]
    ok = False
    if os.environ.get("GLANCE_NO_GNOME_BRIDGE", "") != "1":
        ok = _call("GetState", timeout=3.0) is not None
    _avail_cache = (now, ok)
    return ok


def screenshot() -> Optional[dict]:
    """Capture the whole desktop. Returns {path, stage:{w,h}, monitors:[...]} or None.
    The caller owns (and should delete) the PNG at `path`."""
    fd, path = tempfile.mkstemp(prefix="glance-shot-", suffix=".png")
    os.close(fd)
    out = _call("Screenshot", _q(path), timeout=15.0)
    if not out:
        _unlink(path)
        return None
    try:
        info = json.loads(ast.literal_eval(out.strip())[0])
    except (ValueError, SyntaxError, IndexError, TypeError):
        _unlink(path)
        return None
    if not info.get("ok"):
        _unlink(path)
        return None
    return info


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def _logical(px: float, py: float) -> tuple:
    s = last_scale if last_scale > 0 else 1.0
    return float(px) / s, float(py) / s


class GnomeActuator:
    """Same duck-typed surface as agent.actuation.WindowsActuator, but every
    action is performed inside the compositor. Coordinates arrive in PHYSICAL
    pixels (that's what the shell's coordinate mapping produces)."""

    def left_click(self, x, y):
        lx, ly = _logical(x, y)
        _call("Click", f"{lx:.1f}", f"{ly:.1f}", "1", "1")

    def double_click(self, x, y):
        lx, ly = _logical(x, y)
        _call("Click", f"{lx:.1f}", f"{ly:.1f}", "1", "2")

    def right_click(self, x, y):
        lx, ly = _logical(x, y)
        _call("Click", f"{lx:.1f}", f"{ly:.1f}", "3", "1")

    def move(self, x, y):
        lx, ly = _logical(x, y)
        _call("MoveTo", f"{lx:.1f}", f"{ly:.1f}")

    def scroll(self, x, y, dy):
        lx, ly = _logical(x, y)
        _call("Scroll", f"{lx:.1f}", f"{ly:.1f}", str(int(dy)))

    def type_text(self, text):
        _call("TypeText", _q(str(text)))

    def key(self, combo):
        _call("Key", _q(str(combo)))
