"""Glance launcher dashboard — the control center shown before the companion."""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def show_launcher() -> int:
    """Create the launcher window and run the Qt event loop.
    Returns a process exit code."""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Glance")
    app.setApplicationDisplayName("Glance — Dashboard")

    from .window import LauncherWindow
    win = LauncherWindow()
    win.show()
    return app.exec()
