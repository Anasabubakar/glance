"""Extensions page — skills from MemoryStore, tutor feature toggles."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
)

from ..page_base import BasePage
from ..widgets import Card, FlatButton, DangerButton, SettingRow
from .. import design_tokens as dt


class ExtensionsPage(BasePage):
    title = "Extensions"
    icon = "\U0001F9E9"
    subtitle = "Manage skills and tutor features."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = None
        try:
            from memory_store import MemoryStore
            self._store = MemoryStore()
        except Exception:
            pass

        self.body_layout.addWidget(self.section_label("Learned Skills"))
        self._skills_container = QVBoxLayout()
        self._skills_container.setSpacing(6)
        self.body_layout.addLayout(self._skills_container)

        self.body_layout.addWidget(self.section_label("Tutor Features"))
        tutor_features = [
            ("GLANCE_SLOW_MODE", "Slow Mode", "Longer pauses for learners to absorb information"),
            ("GLANCE_QUIZ_MODE", "Quiz Mode", "Ask comprehension questions after explanations"),
        ]
        for env_key, label, desc in tutor_features:
            checked = os.environ.get(env_key, "0").strip() in ("1", "true", "yes")
            row = SettingRow(label, desc, checked=checked)
            row.toggled.connect(lambda on, ek=env_key: self._toggle(ek, on))
            self.body_layout.addWidget(row)

        self.body_layout.addStretch()

    def on_activate(self):
        while self._skills_container.count():
            item = self._skills_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self._store:
            lbl = QLabel("Memory store unavailable.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._skills_container.addWidget(lbl)
            return

        self._store._load()
        if not self._store.skills:
            lbl = QLabel("No skills learned yet. Glance learns skills during conversations.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._skills_container.addWidget(lbl)
            return

        for name, info in self._store.skills.items():
            card = Card()
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setFont(dt.font(13, dt.QFont.Weight.DemiBold))
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(lbl, 1)
            del_btn = DangerButton("Remove")
            del_btn.setFixedWidth(80)
            del_btn.clicked.connect(lambda _c=False, n=name: self._remove_skill(n))
            row.addWidget(del_btn)
            card.add_layout(row)

            steps = info.get("steps", "") if isinstance(info, dict) else str(info)
            if steps:
                detail = QLabel(steps)
                detail.setFont(dt.FONT_CAPTION)
                detail.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
                detail.setWordWrap(True)
                card.add_widget(detail)

            self._skills_container.addWidget(card)

    def _remove_skill(self, name: str):
        reply = QMessageBox.question(
            self, "Remove Skill",
            f"Remove the skill '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes and self._store:
            self._store.remove_skill(name)
            self._store.save()
            self.on_activate()

    def _toggle(self, env_key: str, on: bool):
        os.environ[env_key] = "1" if on else "0"
        try:
            from config import cfg
            cfg._persist_env(env_key, "1" if on else "0")
        except Exception:
            pass
