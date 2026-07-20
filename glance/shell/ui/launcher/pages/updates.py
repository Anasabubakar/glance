"""
Updates page — version display, GitHub API check, release notes.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, GradientButton, FlatButton, PillBadge
from .. import design_tokens as dt


class _UpdateChecker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        try:
            import httpx
            r = httpx.get(
                "https://api.github.com/repos/Anasabubakar/Glance/releases/latest",
                timeout=15,
                follow_redirects=True,
            )
            if r.status_code == 200:
                j = r.json()
                data["latest"] = j.get("tag_name", "")
                data["name"] = j.get("name", "")
                data["body"] = j.get("body", "")
                data["url"] = j.get("html_url", "")
            else:
                data["error"] = f"GitHub API returned {r.status_code}"
        except Exception as e:
            data["error"] = str(e)[:120]
        self.result.emit(data)


class UpdatesPage(BasePage):
    title = "Updates"
    icon = "⬆"
    subtitle = "Check for new Glance releases."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []

        try:
            import glance
            self._version = glance.__version__
        except Exception:
            self._version = "dev"

        # Current version
        self.body_layout.addWidget(self.section_label("Current Version"))
        ver_card = Card()
        ver_row = QHBoxLayout()
        ver_lbl = QLabel(f"v{self._version}")
        ver_lbl.setFont(dt.font(22, dt.QFont.Weight.Bold))
        ver_lbl.setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")
        ver_row.addWidget(ver_lbl)
        ver_row.addStretch()
        self._badge = PillBadge("Latest", "green")
        ver_row.addWidget(self._badge)
        ver_card.add_layout(ver_row)
        self.body_layout.addWidget(ver_card)

        # Check button
        self._check_btn = GradientButton("Check for Updates")
        self._check_btn.setFixedHeight(40)
        self._check_btn.clicked.connect(self._check)
        self.body_layout.addWidget(self._check_btn)

        # Result card
        self._result_card = Card()
        self._result_label = QLabel("")
        self._result_label.setFont(dt.FONT_BODY)
        self._result_label.setWordWrap(True)
        self._result_card.add_widget(self._result_label)

        self._notes_label = QLabel("")
        self._notes_label.setFont(dt.FONT_CAPTION)
        self._notes_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._notes_label.setWordWrap(True)
        self._notes_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._result_card.add_widget(self._notes_label)
        self._result_card.setVisible(False)
        self.body_layout.addWidget(self._result_card)
        self.body_layout.addStretch()

    def _check(self):
        self._check_btn.setEnabled(False)
        self._check_btn.setText("Checking…")
        w = _UpdateChecker()
        w.result.connect(self._apply)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply(self, data: dict):
        self._check_btn.setEnabled(True)
        self._check_btn.setText("Check for Updates")
        self._result_card.setVisible(True)

        if "error" in data:
            self._result_label.setText(f"Could not check: {data['error']}")
            self._result_label.setStyleSheet(f"color: {dt.ERROR.name()};")
            self._notes_label.setText("")
            return

        latest = data.get("latest", "").lstrip("v")
        current = self._version.lstrip("v")

        if latest and latest != current:
            self._result_label.setText(
                f"New version available: v{latest}  (you have v{current})"
            )
            self._result_label.setStyleSheet(f"color: {dt.WARNING.name()};")
            self._badge.setText("Update Available")
            self._badge.setStyleSheet(
                "background: rgba(251,146,60,0.1); color: #FB923C; "
                "border: 1px solid rgba(251,146,60,0.2); "
                "border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 500;"
            )
        else:
            self._result_label.setText("You're running the latest version.")
            self._result_label.setStyleSheet(f"color: {dt.SUCCESS.name()};")

        body = data.get("body", "")
        if body:
            self._notes_label.setText(body[:2000])
