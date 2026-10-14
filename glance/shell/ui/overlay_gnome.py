"""
Overlay backend for GNOME: forwards the CursorOverlay API to the Glance Cursor
shell extension over D-Bus (app.glance.Overlay).

Why: on GNOME/Wayland an app window can't stay above other windows, can't follow
the pointer, and can't live on every workspace. The extension draws the buddy
inside GNOME Shell itself, so it is above every window and workspace, never shows
in the taskbar or alt-tab, and tracks the pointer on the compositor's frame clock.

This class has the same public API as ui.overlay.CursorOverlay, so main.py wires
it identically. The extension shows the buddy only while this process owns the
bus name `app.glance.Companion`, so it disappears the instant Glance exits.
"""

import time

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface

SERVICE = "app.glance.Overlay"
PATH = "/app/glance/Overlay"
COMPANION = "app.glance.Companion"

MODE_IDLE = "idle"

# Audio level arrives per mic chunk (often >60/s); the extension smooths it, so
# 25 Hz over the bus is plenty and keeps D-Bus quiet.
_AUDIO_MIN_INTERVAL = 0.04


class GnomeOverlay(QObject):

    def __init__(self):
        super().__init__()
        self._bus = QDBusConnection.sessionBus()
        self._iface = QDBusInterface(SERVICE, PATH, SERVICE, self._bus)
        self._last_audio = 0.0
        self._registered = False

    # ── lifecycle ─────────────────────────────────────────────────────────
    def show(self):
        """Claiming the companion name is what makes the extension show the buddy."""
        if not self._registered:
            self._registered = self._bus.registerService(COMPANION)

    def hide(self):
        self.close()

    def close(self):
        if self._registered:
            self._bus.unregisterService(COMPANION)
            self._registered = False

    def _call(self, method: str, *args):
        if self._iface.isValid():
            self._iface.asyncCall(method, *args)

    # ── CursorOverlay API ────────────────────────────────────────────────
    @pyqtSlot(str)
    def set_mode(self, mode: str):
        self._call("SetMode", str(mode))

    @pyqtSlot(float)
    def set_audio_level(self, rms: float):
        now = time.monotonic()
        if now - self._last_audio >= _AUDIO_MIN_INTERVAL:
            self._last_audio = now
            self._call("SetAudioLevel", float(rms))

    @pyqtSlot(float, float, str)
    def point_at(self, x: float, y: float, label: str = ""):
        self._call("PointAt", float(x), float(y), str(label or ""))

    @pyqtSlot(bool)
    def set_slow_mode(self, enabled: bool):
        self._call("SetSlowMode", bool(enabled))

    @pyqtSlot(bool)
    def set_point_hold(self, hold: bool):
        self._call("SetPointHold", bool(hold))

    @pyqtSlot()
    def release_point(self):
        self._call("ReleasePoint")

    @pyqtSlot()
    def hide_cursor(self):
        self._call("HideCursor")

    @pyqtSlot(float, float, float, float)
    def add_arrow(self, x1, y1, x2, y2, ttl: float = 8.0):
        self._call("AddArrow", float(x1), float(y1), float(x2), float(y2), float(ttl))

    @pyqtSlot(float, float, float)
    def add_circle(self, x, y, radius: float = 30.0, ttl: float = 8.0):
        self._call("AddCircle", float(x), float(y), float(radius), float(ttl))

    @pyqtSlot(float, float, float)
    def add_underline(self, x, y, width, ttl: float = 8.0):
        self._call("AddUnderline", float(x), float(y), float(width), float(ttl))

    @pyqtSlot(float, float, str)
    def add_text(self, x, y, text, ttl: float = 8.0):
        self._call("AddText", float(x), float(y), str(text), float(ttl))

    @pyqtSlot()
    def clear_annotations(self):
        self._call("ClearAnnotations")
