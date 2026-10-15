"""
Updates — compare this version to the latest GitHub release, with notes and a
one-click download page.
"""

from __future__ import annotations

import re
import threading

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Card, FlatButton, GradientButton, IconTile, PillBadge

_REPO = "Anasabubakar/glance"


def version_tuple(v: str) -> tuple:
    """'v0.3.10' -> (0, 3, 10); unparsable -> (0,)."""
    nums = re.findall(r"\d+", v.split("-")[0])
    return tuple(int(n) for n in nums) or (0,)


def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)


def clean_notes(md: str, limit: int = 1400) -> str:
    """Release notes as readable plain text (drop markdown markers)."""
    out = []
    for line in md.splitlines():
        line = re.sub(r"^#{1,6}\s*", "", line).replace("**", "").replace("`", "")
        out.append(line.rstrip())
    text = "\n".join(out).strip()
    return text if len(text) <= limit else text[:limit].rsplit("\n", 1)[0] + "\n…"


class _UpdateChecker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data: dict = {}
        try:
            import httpx
            r = httpx.get(f"https://api.github.com/repos/{_REPO}/releases/latest",
                          timeout=15, follow_redirects=True)
            if r.status_code == 200:
                j = r.json()
                data.update(latest=j.get("tag_name", ""), name=j.get("name", ""),
                            body=j.get("body", "") or "", url=j.get("html_url", ""))
            else:
                data["error"] = f"GitHub answered {r.status_code}"
        except Exception as e:
            data["error"] = "Couldn't reach GitHub" if "onnect" in type(e).__name__ else type(e).__name__
        self.result.emit(data)


class UpdatesPage(BasePage):
    title = "Updates"
    icon = "refresh"
    subtitle = "Check for new Glance releases."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []
        self._checked = False
        self._url = f"https://github.com/{_REPO}/releases/latest"
        try:
            import glance
            self._version = glance.__version__
        except Exception:
            self._version = "0.0.0"

        card = Card(padding=22)
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(IconTile("refresh", 48), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        tr = QHBoxLayout()
        v = QLabel(f"Glance {self._version}")
        v.setFont(dt.font(20, dt.QFont.Weight.DemiBold))
        tr.addWidget(v)
        self._pill = PillBadge("Not checked", "default")
        tr.addWidget(self._pill)
        tr.addStretch()
        col.addLayout(tr)
        self._msg = QLabel("Press “Check now” to look for a newer version.")
        self._msg.setFont(dt.font(14))
        self._msg.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._msg.setWordWrap(True)
        col.addWidget(self._msg)
        row.addLayout(col, 1)
        self._check_btn = GradientButton("Check now")
        self._check_btn.clicked.connect(self._check)
        row.addWidget(self._check_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self._get_btn = FlatButton("Download", icon="download")
        self._get_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self._url)))
        self._get_btn.setVisible(False)
        row.addWidget(self._get_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        card.add_layout(row)
        self.body_layout.addWidget(card)

        self._notes_head = self.section_label("What's new")
        self._notes_head.setVisible(False)
        self.body_layout.addWidget(self._notes_head)
        self._notes_card = Card(padding=20)
        self._notes = QLabel("")
        self._notes.setFont(dt.font(13))
        self._notes.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._notes.setWordWrap(True)
        self._notes.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._notes_card.add_widget(self._notes)
        self._notes_card.setVisible(False)
        self.body_layout.addWidget(self._notes_card)
        self.body_layout.addStretch()

    def on_activate(self):
        if not self._checked:
            self._check()

    def _check(self):
        self._checked = True
        self._check_btn.setEnabled(False)
        self._check_btn.setText("Checking…")
        w = _UpdateChecker()
        w.result.connect(self._apply)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply(self, data: dict):
        self._check_btn.setEnabled(True)
        self._check_btn.setText("Check again")
        if "error" in data:
            self._pill.set_state("Couldn't check", "warning")
            self._msg.setText(data["error"] + ". Check your connection and try again.")
            return
        latest = data.get("latest", "")
        self._url = data.get("url") or self._url
        if latest and is_newer(latest, self._version):
            self._pill.set_state("Update available", "accent")
            self._msg.setText(f"{latest.lstrip('v') and 'Version ' + latest.lstrip('v')} is available "
                              f"(you have {self._version}).")
            self._get_btn.setVisible(True)
        else:
            self._pill.set_state("Up to date", "success")
            self._msg.setText("You're running the latest version.")
            self._get_btn.setVisible(False)
        body = clean_notes(data.get("body", ""))
        self._notes.setText(body)
        self._notes_card.setVisible(bool(body))
        self._notes_head.setVisible(bool(body))
