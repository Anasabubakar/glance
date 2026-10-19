"""
Signals from the GNOME extension that are not the hotkey: the Escape "stop" key
(only grabbed while Glance is acting) and recorded user input for Workflow Capture.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import QDBusConnection

SERVICE = "app.glance.Overlay"
PATH = "/app/glance/Overlay"


class GnomeSignals(QObject):
    stop_pressed = pyqtSignal()
    input_event = pyqtSignal(str)          # JSON: {kind, x, y, key, window, t}

    def __init__(self):
        super().__init__()
        bus = QDBusConnection.sessionBus()
        bus.connect(SERVICE, PATH, SERVICE, "StopPressed", self._stop)
        bus.connect(SERVICE, PATH, SERVICE, "InputEvent", self._input)

    @pyqtSlot()
    def _stop(self):
        self.stop_pressed.emit()

    @pyqtSlot(str)
    def _input(self, js: str):
        self.input_event.emit(js)
