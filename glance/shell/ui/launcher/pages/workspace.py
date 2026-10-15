"""
Google Workspace — connect Gmail and Calendar.

Glance reads ~/.glance/google_credentials.json (an OAuth "Desktop app" client you
download from Google Cloud) and caches the sign-in in ~/.glance/google_token.json.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Banner, Card, Divider, FlatButton, GhostButton, IconTile, PillBadge

_DIR = Path.home() / ".glance"
_STEPS = [
    "Open the Google Cloud console and create a project (or pick one).",
    "Enable the Gmail API and the Google Calendar API.",
    "Create an OAuth client ID of type “Desktop app” and download its JSON.",
    "Save it as ~/.glance/google_credentials.json, then ask Glance about your email or calendar. "
    "A browser window asks you to sign in once.",
]


class WorkspacePage(BasePage):
    title = "Google Workspace"
    icon = "briefcase"
    subtitle = "Let Glance read your Gmail and Calendar."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = Card(padding=20)
        self.body_layout.addWidget(self._status)

        self.body_layout.addWidget(self.section_label("How to connect"))
        steps = Card(padding=20)
        steps._layout.setSpacing(14)
        for i, text in enumerate(_STEPS, 1):
            row = QHBoxLayout()
            row.setSpacing(14)
            n = QLabel(str(i))
            n.setFixedSize(26, 26)
            n.setAlignment(Qt.AlignmentFlag.AlignCenter)
            n.setStyleSheet(f"background: {dt.ACCENT_SOFT}; color: #8FA6FF; border-radius: 13px; font-weight: 700;")
            row.addWidget(n, 0, Qt.AlignmentFlag.AlignTop)
            t = QLabel(text)
            t.setWordWrap(True)
            t.setFont(dt.font(14))
            t.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            row.addWidget(t, 1)
            steps.add_layout(row)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        console = FlatButton("Open Google Cloud console", icon="external")
        console.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://console.cloud.google.com/apis/credentials")))
        folder = FlatButton("Open ~/.glance folder", icon="briefcase")
        folder.clicked.connect(self._open_folder)
        actions.addWidget(console)
        actions.addWidget(folder)
        actions.addStretch()
        steps.add_layout(actions)
        self.body_layout.addWidget(steps)
        self.body_layout.addStretch()
        self._render()

    def _open_folder(self):
        _DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(_DIR)])

    def _disconnect(self):
        if QMessageBox.question(self, "Disconnect Google", "Sign out of Google on this computer?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) \
                == QMessageBox.StandardButton.Yes:
            (_DIR / "google_token.json").unlink(missing_ok=True)
            self._render()

    def _render(self):
        self._status.clear_layout()
        creds = (_DIR / "google_credentials.json").is_file()
        token = (_DIR / "google_token.json").is_file()
        title, pill, variant, desc = (
            ("Connected", "Signed in", "success", "Glance can read your Gmail and Calendar.") if creds and token else
            ("Ready to sign in", "Credentials found", "info",
             "Ask Glance about your email or calendar; a browser window will ask you to sign in once.")
            if creds else
            ("Not connected", "Needs credentials", "warning",
             "Follow the steps below to connect your Google account."))
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(IconTile("briefcase", 44), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        tr = QHBoxLayout()
        t = QLabel(title)
        t.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        tr.addWidget(t)
        tr.addWidget(PillBadge(pill, variant))
        tr.addStretch()
        col.addLayout(tr)
        col.addWidget(self.hint_label(desc))
        row.addLayout(col, 1)
        if token:
            b = GhostButton("Disconnect")
            b.clicked.connect(self._disconnect)
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        self._status.add_layout(row)

    def on_activate(self):
        self._render()
