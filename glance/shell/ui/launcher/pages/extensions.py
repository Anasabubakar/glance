"""
Skills — reusable how-tos Glance has learned from you. (Behaviour toggles such as
teacher pace live in Settings.)
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Card, Divider, GhostButton, IconTile


class ExtensionsPage(BasePage):
    title = "Skills"
    icon = "grid"
    subtitle = "Things Glance has learned to do for you."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = None
        try:
            from memory_store import MemoryStore
            self._store = MemoryStore()
        except Exception:
            pass
        self._card = Card(padding=8)
        self._card._layout.setSpacing(0)
        self.body_layout.addWidget(self._card)
        self.body_layout.addStretch()

    def _empty(self, text: str):
        box = QWidget()
        bl = QVBoxLayout(box)
        bl.setContentsMargins(32, 32, 32, 32)
        bl.setSpacing(10)
        bl.addWidget(IconTile("grid", 48), 0, Qt.AlignmentFlag.AlignHCenter)
        t = QLabel("No skills yet")
        t.setFont(dt.font(15, dt.QFont.Weight.DemiBold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(t)
        d = QLabel(text)
        d.setWordWrap(True)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d.setFont(dt.font(13))
        d.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        bl.addWidget(d)
        self._card.add_widget(box)

    def on_activate(self):
        self._card.clear_layout()
        if not self._store:
            self._empty("The memory store isn't available.")
            return
        self._store._load()
        if not self._store.skills:
            self._empty("Teach Glance a routine by saying “remember how to…”, or add one under Memory. "
                        "It will show up here.")
            return
        for i, (name, info) in enumerate(self._store.skills.items()):
            if i:
                self._card.add_widget(Divider())
            row = QHBoxLayout()
            row.setContentsMargins(14, 12, 10, 12)
            col = QVBoxLayout()
            col.setSpacing(3)
            n = QLabel(name)
            n.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            col.addWidget(n)
            steps = info.get("steps", "") if isinstance(info, dict) else str(info)
            if steps:
                col.addWidget(self.hint_label(steps))
            row.addLayout(col, 1)
            rm = GhostButton("Remove", icon="trash")
            rm.clicked.connect(lambda _c=False, nm=name: self._remove_skill(nm))
            row.addWidget(rm, 0, Qt.AlignmentFlag.AlignTop)
            self._card.add_layout(row)

    def _remove_skill(self, name: str):
        if QMessageBox.question(self, "Remove skill", f"Remove the skill “{name}”?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) \
                == QMessageBox.StandardButton.Yes and self._store:
            self._store.remove_skill(name)
            self._store.save()
            self.on_activate()
