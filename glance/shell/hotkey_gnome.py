"""
Push-to-talk hotkey via the Glance Cursor GNOME extension.

On Wayland an app can't see keys typed in other windows, so pynput never fires
for a global hotkey. The extension runs inside the compositor, grabs the combo
(default ctrl+alt+m) and emits HotkeyPressed / HotkeyReleased over D-Bus, which
this class turns into the same on_press / on_release callbacks as
hotkey.GlobalHotkeyMonitor.
"""

from typing import Callable

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface

from config import cfg

SERVICE = "app.glance.Overlay"
PATH = "/app/glance/Overlay"


class GnomeHotkeyMonitor(QObject):

    def __init__(self, on_press: Callable[[], None], on_release: Callable[[], None],
                 hotkey: str | None = None):
        super().__init__()
        self._hotkey = hotkey or cfg.hotkey
        self._on_press = on_press
        self._on_release = on_release
        self._bus = QDBusConnection.sessionBus()
        self._connected = False

    def start(self):
        ok1 = self._bus.connect(SERVICE, PATH, SERVICE, "HotkeyPressed", self._pressed)
        ok2 = self._bus.connect(SERVICE, PATH, SERVICE, "HotkeyReleased", self._released)
        self._connected = bool(ok1 and ok2)
        QDBusInterface(SERVICE, PATH, SERVICE, self._bus).asyncCall("SetHotkey", str(self._hotkey))

    def stop(self):
        if self._connected:
            self._bus.disconnect(SERVICE, PATH, SERVICE, "HotkeyPressed", self._pressed)
            self._bus.disconnect(SERVICE, PATH, SERVICE, "HotkeyReleased", self._released)
            self._connected = False
        QDBusInterface(SERVICE, PATH, SERVICE, self._bus).asyncCall("SetHotkey", "")

    @pyqtSlot()
    def _pressed(self):
        self._on_press()

    @pyqtSlot()
    def _released(self):
        self._on_release()
