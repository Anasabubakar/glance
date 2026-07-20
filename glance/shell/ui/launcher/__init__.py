"""
Glance Desktop Launcher — the premium control center shown before the companion.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from . import design_tokens as dt


def show_launcher() -> int:
    """Create the launcher window and run the Qt event loop.

    Returns a process exit code for the application.
    """
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Glance")
    app.setApplicationDisplayName("Glance — AI Desktop Companion")
    app.setApplicationVersion("1.0.0")

    # Set app-wide icon
    icon = dt.load_icon("glance-flat.png")
    if not icon.isNull():
        app.setWindowIcon(icon)

    from .window import LauncherWindow
    win = LauncherWindow()
    win.show()
    return app.exec()
