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


def _env() -> dict:
    """Environment for the system `gdbus` binary. The PyInstaller bundle points
    LD_LIBRARY_PATH at its own (older) glib, which makes the system gdbus crash
    with "undefined symbol", so every call silently failed in the installed app."""
    env = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    elif getattr(__import__("sys"), "frozen", False):
        env.pop("LD_LIBRARY_PATH", None)
    return env


def _call(method: str, *args: str, timeout: float = 10.0) -> Optional[str]:
    cmd = ["gdbus", "call", "--session", "--dest", SERVICE, "--object-path", PATH,
           "--method", f"{SERVICE}.{method}", *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=_env())
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
        if ok:
            ok = _has_capture()
    _avail_cache = (now, ok)
    return ok


_capable = False


def _has_capture() -> bool:
    """The compositor keeps running the extension code it loaded at login, so right
    after an update it can be an OLD copy with no Screenshot/Click methods."""
    global _capable
    if _capable:
        return True
    try:
        r = subprocess.run(["gdbus", "introspect", "--session", "--dest", SERVICE,
                            "--object-path", PATH], capture_output=True, text=True, timeout=4,
                           env=_env())
        _capable = "Screenshot(" in r.stdout
    except (OSError, subprocess.TimeoutExpired):
        _capable = False
    return _capable


def windows() -> list:
    """Open normal windows (id, title, wm_class, frame rect, focused, minimized...)."""
    out = _call("GetWindows", timeout=3.0)
    if not out:
        return []
    try:
        return json.loads(ast.literal_eval(out.strip())[0])
    except (ValueError, SyntaxError, IndexError, TypeError):
        return []


def window_action(which: str, action: str) -> Optional[dict]:
    """minimize / maximize / unmaximize / close / activate / fullscreen on one window.
    `which` is "focused", a window id, "title:<text>" or "class:<text>"."""
    out = _call("WindowAction", _q(which), _q(action), timeout=5.0)
    if not out:
        return None
    try:
        return json.loads(ast.literal_eval(out.strip())[0])
    except (ValueError, SyntaxError, IndexError, TypeError):
        return None


def get_clipboard(kind: str = "clipboard") -> str:
    """Text on the clipboard ("clipboard") or the current selection ("primary")."""
    out = _call("GetClipboard", _q(kind), timeout=3.0)
    if not out:
        return ""
    try:
        return ast.literal_eval(out.strip())[0]
    except (ValueError, SyntaxError, IndexError, TypeError):
        return ""


def set_clipboard(text: str) -> None:
    _call("SetClipboard", _q(str(text)), timeout=3.0)


def switch_workspace(index: int) -> None:
    _call("SwitchWorkspace", str(int(index)), timeout=3.0)


def move_window_to_workspace(which: str, index: int):
    out = _call("MoveWindowToWorkspace", _q(which), str(int(index)), timeout=3.0)
    try:
        return json.loads(ast.literal_eval(out.strip())[0]) if out else None
    except (ValueError, SyntaxError, IndexError, TypeError):
        return None


def workspaces() -> dict:
    out = _call("GetWorkspaces", timeout=3.0)
    try:
        return json.loads(ast.literal_eval(out.strip())[0]) if out else {}
    except (ValueError, SyntaxError, IndexError, TypeError):
        return {}


def set_stop_grab(on: bool) -> None:
    _call("SetStopGrab", "true" if on else "false", timeout=3.0)


def set_recording(on: bool) -> None:
    _call("SetRecording", "true" if on else "false", timeout=3.0)


def state() -> Optional[dict]:
    """The overlay's live state: {pointer:{x,y}, pos:{x,y}, stage:{w,h}, ...}."""
    out = _call("GetState", timeout=2.0)
    if not out:
        return None
    try:
        return json.loads(ast.literal_eval(out.strip())[0])
    except (ValueError, SyntaxError, IndexError, TypeError):
        return None


_win_ok = False


def supports_windows() -> bool:
    """False right after an update: the extension still loaded in the session may predate
    the window API (GetWindows), which only a fresh login picks up."""
    global _win_ok
    if _win_ok:
        return True
    try:
        r = subprocess.run(["gdbus", "introspect", "--session", "--dest", SERVICE,
                            "--object-path", PATH], capture_output=True, text=True, timeout=4, env=_env())
        _win_ok = "GetWindows(" in r.stdout
    except (OSError, subprocess.TimeoutExpired):
        _win_ok = False
    return _win_ok


def outdated() -> bool:
    """True when the extension is running but is an old copy: log out and back in."""
    if os.environ.get("GLANCE_NO_GNOME_BRIDGE", "") == "1":
        return False
    return _call("GetState", timeout=3.0) is not None and not _has_capture()


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
        text = str(text)
        _call("TypeText", _q(text))
        time.sleep(len(text) * 0.016 + 0.15)       # the shell types in the background: wait for it

    def triple_click(self, x, y):
        lx, ly = _logical(x, y)
        _call("Click", f"{lx:.1f}", f"{ly:.1f}", "1", "3")

    def middle_click(self, x, y):
        lx, ly = _logical(x, y)
        _call("Click", f"{lx:.1f}", f"{ly:.1f}", "2", "1")

    def click_with(self, x, y, mods, button=1, count=1):
        """ctrl+click, shift+click, ...  mods like "ctrl" or "ctrl+shift"."""
        lx, ly = _logical(x, y)
        _call("ClickWith", f"{lx:.1f}", f"{ly:.1f}", str(int(button)), str(int(count)), _q(str(mods)))

    def drag(self, x1, y1, x2, y2, ms=700):
        """Press at the first point, move to the second, release (drag and drop, select)."""
        ax, ay = _logical(x1, y1)
        bx, by = _logical(x2, y2)
        _call("Drag", f"{ax:.1f}", f"{ay:.1f}", f"{bx:.1f}", f"{by:.1f}", "1", str(int(ms)))
        time.sleep(ms / 1000.0 + 0.4)

    def draw(self, strokes, ms_per_stroke=900):
        """Freehand: each stroke is a list of (x, y) points followed with the button held."""
        import json as _j
        for st in strokes:
            if len(st) < 2:
                continue
            pts = [list(_logical(x, y)) for x, y in st]
            ms = max(400, min(ms_per_stroke, 12000))
            _call("DragPath", _q(_j.dumps([[round(a, 1), round(b, 1)] for a, b in pts])), "1", str(ms))
            time.sleep(ms / 1000.0 + 0.5)

    def key(self, combo):
        _call("Key", _q(str(combo)))
