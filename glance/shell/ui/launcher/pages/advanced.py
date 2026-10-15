"""
Advanced — power-user settings and reset. Secrets (API keys) are deliberately NOT
listed here: they live under AI & Keys and are never shown in full.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Banner, Card, DangerButton, GradientButton

_EDITABLE = [
    ("GLANCE_HOTKEY", "Push-to-talk hotkey, e.g. ctrl+alt+m"),
    ("GLANCE_ACTIVE_LLM", "Force a provider: cloud, gemini, claude, openai, ollama, custom"),
    ("GLANCE_ACTIVE_MODEL", "Pin one model id (blank = automatic)"),
    ("GLANCE_CLOUD_URL", "Glance Cloud address"),
    ("GLANCE_NO_CLOUD", "Set to 1 to never fall back to Glance Cloud"),
    ("GLANCE_OVERLAY", "Cursor overlay: gnome or qt"),
    ("OLLAMA_HOST", "Where Ollama listens, e.g. http://localhost:11434"),
]


def _user_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Glance"


class AdvancedPage(BasePage):
    title = "Advanced"
    icon = "terminal"
    subtitle = "Power-user settings and reset."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        self.body_layout.addWidget(self.section_label("Environment settings"))
        self.body_layout.addWidget(self.hint_label(
            "These are saved to your settings file. Most need a restart of Glance to take effect."))
        self._table = QTableWidget(len(_EDITABLE), 3)
        self._table.setHorizontalHeaderLabels(["Setting", "Value", "What it does"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(40)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setFrameShape(QTableWidget.Shape.NoFrame)
        self._table.setStyleSheet(f"""
            QTableWidget {{ background: {dt.BG_CARD.name()}; border: 1px solid {dt.BORDER_CSS};
                            border-radius: {dt.CARD_RADIUS}px; gridline-color: transparent; outline: none; }}
            QTableWidget::item {{ padding: 0 12px; border-bottom: 1px solid {dt.BORDER_CSS}; }}
            QTableWidget::item:selected {{ background: {dt.ACCENT_SOFT}; color: {dt.TEXT_PRIMARY.name()}; }}
            QHeaderView {{ background: transparent; border: none; }}
            QTableCornerButton::section {{ background: transparent; border: none; }}
            QHeaderView::section {{ background: transparent; color: {dt.TEXT_DIM.name()}; border: none;
                                    border-bottom: 1px solid {dt.BORDER_CSS}; padding: 10px 12px;
                                    font-size: 11px; font-weight: 600; text-align: left; }}
        """)
        self._table.setMinimumHeight(40 * (len(_EDITABLE) + 1) + 8)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for i, (key, _d) in enumerate(_EDITABLE):
            k = QTableWidgetItem(key)
            k.setFlags(k.flags() & ~Qt.ItemFlag.ItemIsEditable)
            k.setForeground(dt.TEXT_MUTED)
            self._table.setItem(i, 0, k)
            d = QTableWidgetItem(_d)
            d.setFlags(d.flags() & ~Qt.ItemFlag.ItemIsEditable)
            d.setForeground(dt.TEXT_DIM)
            self._table.setItem(i, 2, d)
        self.body_layout.addWidget(self._table)
        row = QHBoxLayout()
        save = GradientButton("Save changes")
        save.clicked.connect(self._save_all)
        row.addWidget(save)
        row.addStretch()
        self.body_layout.addLayout(row)

        self.body_layout.addWidget(self.section_label("Reset"))
        card = Card(padding=20)
        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel("Reset Glance")
        t.setFont(dt.font(14, dt.QFont.Weight.Medium))
        col.addWidget(t)
        col.addWidget(self.hint_label("Clears your saved settings and keys on this computer. You'll set Glance up "
                                      "again from scratch. This can't be undone."))
        r = QHBoxLayout()
        r.addLayout(col, 1)
        btn = DangerButton("Reset…")
        btn.clicked.connect(self._reset)
        r.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)
        card.add_layout(r)
        self.body_layout.addWidget(card)
        self.body_layout.addStretch()

    def on_activate(self):
        for i, (key, _d) in enumerate(_EDITABLE):
            val = os.environ.get(key, "")
            self._table.setItem(i, 1, QTableWidgetItem(val))

    def _save_all(self):
        if not self._cfg:
            return
        values = {}
        for i, (key, _d) in enumerate(_EDITABLE):
            item = self._table.item(i, 1)
            if item and item.text().strip():
                values[key] = item.text().strip()
        self._cfg.save_env_values(values)
        QMessageBox.information(self, "Saved", "Settings saved. Restart Glance to apply them.")

    def _reset(self):
        if QMessageBox.question(
                self, "Reset Glance",
                "This clears your saved settings and API keys from this computer.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            env_path = _user_dir() / ".env"
            if not getattr(sys, "frozen", False):
                env_path = Path(__file__).parents[3] / ".env"
            if env_path.exists():
                env_path.write_text("")
            for name in (".setup_complete", "cloud_key"):
                (_user_dir() / name).unlink(missing_ok=True)
            QMessageBox.information(self, "Reset complete", "Glance has been reset. Restart it to set up again.")
        except Exception as e:
            QMessageBox.warning(self, "Couldn't reset", str(e))
