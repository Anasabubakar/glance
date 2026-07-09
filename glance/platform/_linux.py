"""Linux platform backend — xdg-open, xdotool, AT-SPI2, subprocess with setsid."""
from __future__ import annotations

import os
import subprocess
from typing import Optional, Tuple


def open_path(path: str) -> None:
    """Open a file or folder with the OS default handler."""
    subprocess.Popen(["xdg-open", path],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def detached_popen(args: list[str], **kwargs) -> subprocess.Popen:
    """Spawn a process detached from the current session."""
    return subprocess.Popen(
        args,
        stdout=kwargs.pop("stdout", subprocess.DEVNULL),
        stderr=kwargs.pop("stderr", subprocess.DEVNULL),
        start_new_session=True,
        **kwargs,
    )


def get_dpi_scale() -> float:
    """Primary monitor DPI scale. Tries Qt first, then Xrandr, then GDK_SCALE."""
    try:
        scale = os.environ.get("GDK_SCALE")
        if scale:
            return max(1.0, float(scale))
    except (ValueError, TypeError):
        pass
    try:
        scale = os.environ.get("QT_SCALE_FACTOR")
        if scale:
            return max(1.0, float(scale))
    except (ValueError, TypeError):
        pass
    try:
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


def active_window_title() -> str:
    """Title of the foreground window via xdotool."""
    try:
        out = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowname"],
            stderr=subprocess.DEVNULL, text=True, timeout=2
        )
        return out.strip()
    except Exception:
        pass
    try:
        out = subprocess.check_output(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            stderr=subprocess.DEVNULL, text=True, timeout=2
        )
        wid = out.strip().split()[-1]
        if wid and wid != "0x0":
            name_out = subprocess.check_output(
                ["xprop", "-id", wid, "WM_NAME"],
                stderr=subprocess.DEVNULL, text=True, timeout=2
            )
            if '"' in name_out:
                return name_out.split('"', 1)[1].rsplit('"', 1)[0]
    except Exception:
        pass
    return ""


def tidy_desktop_icons() -> None:
    """No-op on Linux — desktop icon layout is managed by the file manager."""
    pass


def snap_to_element(vx: float, vy: float) -> Optional[Tuple[float, float]]:
    """Snap a screen coordinate to the nearest small UI control via AT-SPI2.
    Returns (cx, cy) or None."""
    try:
        import pyatspi
    except ImportError:
        return None
    try:
        desktop = pyatspi.Registry.getDesktop(0)
        target = _atspi_element_at_point(desktop, int(vx), int(vy))
        if target is None:
            return None
        ext = target.queryComponent()
        bbox = ext.getExtents(pyatspi.DESKTOP_COORDS)
        w, h = bbox.width, bbox.height
        if w <= 1 or h <= 1 or w > 600 or h > 360:
            return None
        cx, cy = bbox.x + w / 2.0, bbox.y + h / 2.0
        dist = ((cx - vx) ** 2 + (cy - vy) ** 2) ** 0.5
        if dist > 30:
            return None
        return (cx, cy)
    except Exception:
        return None


def _atspi_element_at_point(desktop, x: int, y: int):
    """Find the deepest AT-SPI2 accessible element at (x, y)."""
    try:
        import pyatspi
    except ImportError:
        return None
    for app in desktop:
        try:
            comp = app.queryComponent()
        except Exception:
            continue
        try:
            child = comp.getAccessibleAtPoint(x, y, pyatspi.DESKTOP_COORDS)
            if child is None:
                continue
            while True:
                try:
                    inner_comp = child.queryComponent()
                    deeper = inner_comp.getAccessibleAtPoint(
                        x, y, pyatspi.DESKTOP_COORDS)
                    if deeper is None or deeper == child:
                        break
                    child = deeper
                except Exception:
                    break
            return child
        except Exception:
            continue
    return None


def find_ui_element(query: str, min_score: float = 0.5):
    """Walk the AT-SPI2 tree for the focused app, find best match.
    Returns a dict with keys: name, type, x, y, w, h — or None."""
    try:
        import pyatspi
    except ImportError:
        return None
    try:
        desktop = pyatspi.Registry.getDesktop(0)
    except Exception:
        return None

    from difflib import SequenceMatcher
    best_score = 0.0
    best_result = None
    visited = 0
    MAX_NODES = 3500

    def _score(q, name, role_name):
        q_low = q.lower()
        n_low = (name or "").lower()
        if q_low == n_low:
            return 1.0
        if q_low in n_low:
            return 0.85
        return SequenceMatcher(None, q_low, n_low).ratio()

    def _walk(obj, depth=0):
        nonlocal visited, best_score, best_result
        if visited >= MAX_NODES or depth > 40:
            return
        visited += 1
        try:
            name = obj.name or ""
            role_name = obj.getRoleName() or ""
        except Exception:
            return
        try:
            comp = obj.queryComponent()
            bbox = comp.getExtents(pyatspi.DESKTOP_COORDS)
            if bbox.width > 0 and bbox.height > 0:
                score = _score(query, name, role_name)
                if score > best_score and score >= min_score:
                    best_score = score
                    best_result = {
                        "name": name,
                        "type": role_name,
                        "x": bbox.x,
                        "y": bbox.y,
                        "w": bbox.width,
                        "h": bbox.height,
                    }
        except Exception:
            pass
        try:
            for i in range(obj.childCount):
                _walk(obj.getChildAtIndex(i), depth + 1)
        except Exception:
            pass

    for app in desktop:
        try:
            _walk(app)
        except Exception:
            continue
    return best_result


APP_LAUNCHERS: dict[str, list[str]] = {
    "steam": ["steam"],
    "discord": ["discord"],
    "spotify": ["spotify"],
    "telegram": ["telegram-desktop", "telegram"],
    "slack": ["slack"],
    "notion": ["notion-app", "notion"],
    "firefox": ["firefox"],
    "chrome": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"],
    "code": ["code"],
    "vscode": ["code"],
    "files": ["nautilus", "thunar", "dolphin", "nemo", "pcmanfm"],
    "terminal": ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"],
    "text editor": ["gedit", "kate", "mousepad", "xed"],
    "calculator": ["gnome-calculator", "kcalc", "galculator"],
}


def launch_app(name: str) -> bool:
    """Launch a Linux app by name. Returns True on success."""
    name = (name or "").strip()
    if not name:
        return False
    for cand in APP_LAUNCHERS.get(name.lower(), []):
        try:
            subprocess.Popen(
                [cand], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except FileNotFoundError:
            continue
        except Exception:
            continue
    try:
        subprocess.Popen(
            ["xdg-open", name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False
