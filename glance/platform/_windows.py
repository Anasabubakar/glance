"""Windows platform backend — ctypes.windll, comtypes, uiautomation, os.startfile."""
from __future__ import annotations

import os
import subprocess
from typing import Optional, Tuple


def open_path(path: str) -> None:
    """Open a file or folder with the OS default handler."""
    try:
        os.startfile(path)
    except Exception:
        subprocess.Popen(["explorer", path])


def detached_popen(args: list[str], **kwargs) -> subprocess.Popen:
    """Spawn a process detached from the current console."""
    return subprocess.Popen(
        args,
        stdout=kwargs.pop("stdout", subprocess.DEVNULL),
        stderr=kwargs.pop("stderr", subprocess.DEVNULL),
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        **kwargs,
    )


def get_dpi_scale() -> float:
    """Primary monitor DPI scale (1.0 = 100%, 1.5 = 150%)."""
    try:
        import ctypes
        u = ctypes.windll.user32
        u.SetProcessDPIAware()
        gdfs = getattr(u, "GetDpiForSystem", None)
        if gdfs:
            return max(1.0, gdfs() / 96.0)
    except Exception:
        pass
    return 1.0


def active_window_title() -> str:
    """Title of the foreground window."""
    try:
        import ctypes
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return ""
        n = u.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value or ""
    except Exception:
        return ""


def tidy_desktop_icons() -> None:
    """Sort desktop icons by name via Explorer COM or legacy WM_COMMAND."""
    try:
        import comtypes
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
        import comtypes.client
        from comtypes.automation import VARIANT
        shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
        disp = shell.Windows().FindWindowSW(VARIANT(), VARIANT(), 8, 0, 1)
        disp.Document.SortColumns = "prop:System.ItemNameDisplay;"
        return
    except Exception:
        pass
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        WM_COMMAND, SORT_BY_NAME = 0x0111, 0x7021
        found = []
        prog = u.FindWindowW("Progman", None)
        h = u.FindWindowExW(prog, 0, "SHELLDLL_DefView", None)
        if h:
            found.append(h)

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def _enum(hwnd, _l):
            dv = u.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
            if dv and dv not in found:
                found.append(dv)
            return True
        u.EnumWindows(_enum, 0)
        for dv in found:
            u.PostMessageW(dv, WM_COMMAND, SORT_BY_NAME, 0)
    except Exception:
        pass


def snap_to_element(vx: float, vy: float) -> Optional[Tuple[float, float]]:
    """Snap a screen coordinate to the center of the small UI control under it.
    Returns (cx, cy) or None to keep the original coordinate."""
    try:
        import uiautomation as auto
        ctrl = auto.ControlFromPoint(int(vx), int(vy))
        if ctrl is None:
            return None
        r = ctrl.BoundingRectangle
        w, h = r.right - r.left, r.bottom - r.top
        if w <= 1 or h <= 1 or w > 600 or h > 360:
            return None
        cx, cy = r.left + w / 2.0, r.top + h / 2.0
        dist = ((cx - vx) ** 2 + (cy - vy) ** 2) ** 0.5
        if dist > 30:
            return None
        return (cx, cy)
    except Exception:
        return None


def find_ui_element(query: str, min_score: float = 0.5):
    """Walk the UIA tree for the foreground window, find best match.
    Returns a dict with keys: name, type, x, y, w, h — or None."""
    try:
        import uiautomation as auto
    except ImportError:
        return None
    try:
        root = auto.GetForegroundControl()
        if root is None:
            root = auto.GetRootControl()
    except Exception:
        return None

    from glance.shell.ai.hybrid_pointer import _score_match
    best_score = 0.0
    best_result = None
    queue = [(root, 0)]
    visited = 0
    MAX_NODES, MAX_DEPTH = 3500, 40

    while queue and visited < MAX_NODES:
        node, depth = queue.pop(0)
        visited += 1
        try:
            name = node.Name or ""
            ctrl_type = node.ControlTypeName or ""
            rect = node.BoundingRectangle
        except Exception:
            continue
        if rect and rect.width() > 0 and rect.height() > 0:
            score = _score_match(query, name, ctrl_type)
            if score > best_score and score >= min_score:
                best_score = score
                best_result = {
                    "name": name,
                    "type": ctrl_type,
                    "x": rect.left,
                    "y": rect.top,
                    "w": rect.width(),
                    "h": rect.height(),
                }
        if depth < MAX_DEPTH:
            try:
                for child in node.GetChildren():
                    queue.append((child, depth + 1))
            except Exception:
                pass
    return best_result


APP_LAUNCHERS = {
    "steam": [r"C:\Program Files (x86)\Steam\steam.exe", "steam://open/main"],
    "discord": [r"%LOCALAPPDATA%\Discord\Update.exe|--processStart|Discord.exe",
                "discord://"],
    "spotify": [r"%APPDATA%\Spotify\Spotify.exe", "spotify:"],
    "epic games": ["com.epicgames.launcher://apps"],
    "epic": ["com.epicgames.launcher://apps"],
    "telegram": [r"%APPDATA%\Telegram Desktop\Telegram.exe", "tg://"],
    "slack": [r"%LOCALAPPDATA%\Microsoft\WindowsApps\Slack.exe",
              r"%LOCALAPPDATA%\slack\slack.exe",
              r"C:\Program Files\Slack\slack.exe"],
    "notion": [r"%LOCALAPPDATA%\Programs\Notion\Notion.exe", "notion://"],
}


def launch_app(name: str) -> bool:
    """Launch a Windows app. Returns True on success."""
    name = (name or "").strip()
    if not name:
        return False
    for cand in APP_LAUNCHERS.get(name.lower(), []):
        if "://" in cand or cand.endswith(":"):
            try:
                os.startfile(cand)
                return True
            except Exception:
                continue
        parts = [os.path.expandvars(p) for p in cand.split("|")]
        if os.path.isfile(parts[0]):
            try:
                subprocess.Popen(parts)
                return True
            except Exception:
                continue
    try:
        subprocess.Popen(["cmd", "/c", "start", "", name],
                         creationflags=0x08000000)
        return True
    except Exception:
        try:
            os.startfile(name)
            return True
        except Exception:
            return False
