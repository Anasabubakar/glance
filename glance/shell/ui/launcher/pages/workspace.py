"""Workspace page — Google Workspace status and configuration."""

import os
from PyQt6.QtWidgets import QLabel, QVBoxLayout

from ..page_base import BasePage
from ..widgets import Card, StatusDot
from .. import design_tokens as dt


class WorkspacePage(BasePage):
    title = "Workspace"
    icon = "\U0001F4BC"
    subtitle = "Google Workspace integration status."

    def __init__(self, parent=None):
        super().__init__(parent)

        self.body_layout.addWidget(self.section_label("Google Workspace"))

        self._gmail_card = Card()
        self._gmail_status = StatusDot(dt.TEXT_DIM)
        self._gmail_label = QLabel("Gmail: checking…")
        self._gmail_label.setFont(dt.FONT_BODY)
        self._gmail_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        from PyQt6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        row.addWidget(self._gmail_status)
        row.addWidget(self._gmail_label)
        row.addStretch()
        self._gmail_card.add_layout(row)
        self.body_layout.addWidget(self._gmail_card)

        self._cal_card = Card()
        self._cal_status = StatusDot(dt.TEXT_DIM)
        self._cal_label = QLabel("Calendar: checking…")
        self._cal_label.setFont(dt.FONT_BODY)
        self._cal_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        row2 = QHBoxLayout()
        row2.addWidget(self._cal_status)
        row2.addWidget(self._cal_label)
        row2.addStretch()
        self._cal_card.add_layout(row2)
        self.body_layout.addWidget(self._cal_card)

        self.body_layout.addWidget(self.hint_label(
            "Google Workspace integration requires OAuth credentials. "
            "Set GOOGLE_CREDENTIALS_FILE in your .env to the path of your credentials.json."
        ))

        self.body_layout.addStretch()

    def on_activate(self):
        creds = os.environ.get("GOOGLE_CREDENTIALS_FILE", "")
        has_creds = bool(creds) and os.path.isfile(creds)

        if has_creds:
            self._gmail_status.set_color(dt.SUCCESS)
            self._gmail_label.setText("Gmail: configured")
            self._cal_status.set_color(dt.SUCCESS)
            self._cal_label.setText("Calendar: configured")
        else:
            self._gmail_status.set_color(dt.TEXT_DIM)
            self._gmail_label.setText("Gmail: not configured")
            self._cal_status.set_color(dt.TEXT_DIM)
            self._cal_label.setText("Calendar: not configured")
