"""
Pick the cursor-overlay backend.

GNOME  → the Glance Cursor shell extension (always above every window and
         workspace, no taskbar entry, follows the pointer). Installed into the
         user's extensions dir on first run; GNOME on Wayland only discovers a
         new extension at the next login, so until then we fall back to the Qt
         overlay and tell the user once.
Others → the Qt overlay window (hardened for X11 inside ui/overlay.py).

Override with GLANCE_OVERLAY=qt|gnome.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

UUID = "glance-cursor@glance.app"
SERVICE = "app.glance.Overlay"


def _bundled_extension() -> Path | None:
    here = Path(__file__).resolve().parent
    for base in (here.parent, Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", "") else None):
        if base and (base / "gnome_ext" / UUID / "metadata.json").exists():
            return base / "gnome_ext" / UUID
    return None


def _user_ext_dir() -> Path:
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(data) / "gnome-shell" / "extensions" / UUID


def is_gnome() -> bool:
    return (sys.platform.startswith("linux")
            and "gnome" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower())


def extension_active() -> bool:
    """True when the extension is loaded in the running shell (its bus name exists)."""
    try:
        from PyQt6.QtDBus import QDBusConnection
        return QDBusConnection.sessionBus().interface().isServiceRegistered(SERVICE).value()
    except Exception:
        return False


SYSTEM_EXT = Path("/usr/share/gnome-shell/extensions") / UUID


def _system_copy_current(src: Path) -> bool:
    """True when the .deb installed the same extension system-wide (it is then loaded at login
    with no per-user copy, which would otherwise override it and keep old code running)."""
    try:
        return (SYSTEM_EXT / "extension.js").read_bytes() == (src / "extension.js").read_bytes() \
            and (SYSTEM_EXT / "motion.js").read_bytes() == (src / "motion.js").read_bytes()
    except OSError:
        return False


def _install_extension() -> bool:
    """Make sure GNOME will load the matching extension at the next login and that it is
    enabled. Returns True if anything changed."""
    src, dst = _bundled_extension(), _user_ext_dir()
    if src is None:
        return False
    changed = False
    if _system_copy_current(src):
        if dst.exists() and dst.name == UUID:           # a stale per-user copy would win: remove ours
            try:
                shutil.rmtree(dst)
                changed = True
            except OSError:
                pass
    else:
        try:
            if not dst.exists() or (dst / "extension.js").read_bytes() != (src / "extension.js").read_bytes() \
                    or (dst / "motion.js").read_bytes() != (src / "motion.js").read_bytes():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                changed = True
        except OSError:
            return False
    try:
        cur = subprocess.run(["gsettings", "get", "org.gnome.shell", "enabled-extensions"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        if UUID not in cur:
            items = [s.strip().strip("'") for s in cur.strip("[]@as ").split(",") if s.strip()]
            new = "[" + ", ".join(f"'{i}'" for i in items + [UUID]) + "]"
            subprocess.run(["gsettings", "set", "org.gnome.shell", "enabled-extensions", new],
                           capture_output=True, timeout=5)
            changed = True
    except Exception:
        pass
    return changed


def create_overlay():
    """Returns (overlay, note). `note` is a one-line user message or None."""
    forced = os.environ.get("GLANCE_OVERLAY", "").lower()
    if forced != "qt" and is_gnome():
        _install_extension()
        if extension_active():
            from ui.overlay_gnome import GnomeOverlay
            return GnomeOverlay(), None
        from ui.overlay import CursorOverlay
        # Installed but not loaded yet: GNOME on Wayland picks up new extensions
        # only at the next login.
        note = ("Glance installed its always-on-top cursor for GNOME. "
                "Log out and back in once to turn it on."
                if (_user_ext_dir().exists() or SYSTEM_EXT.exists()) else None)
        return CursorOverlay(), note
    from ui.overlay import CursorOverlay
    return CursorOverlay(), None
