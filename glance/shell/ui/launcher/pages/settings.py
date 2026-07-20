"""
Settings page — all toggles, hotkey configuration.
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
)
from PyQt6.QtCore import Qt

from ..page_base import BasePage
from ..widgets import Card, SettingRow, FlatButton, PillBadge
from .. import design_tokens as dt

_TOGGLES = [
    ("GLANCE_WEB_SEARCH",   "Web Search",     "Allow Glance to search the web for answers"),
    ("GLANCE_WAKE_WORD",    "Wake Word",       "Activate with voice using 'Hey Glance'"),
    ("GLANCE_SLOW_MODE",    "Slow Mode",       "Add pauses for learners — tutor feature"),
    ("GLANCE_QUIZ_MODE",    "Quiz Mode",       "Ask comprehension questions — tutor feature"),
    ("GLANCE_PRIVACY",      "Privacy Guard",   "Blur sensitive content during screen reading"),
    ("GLANCE_CODE_MODE",    "Code Mode",       "Optimize responses for programming tasks"),
    ("GLANCE_MULTILINGUAL", "Multilingual",    "Support multiple languages in voice input"),
    ("GLANCE_OCR_FALLBACK", "OCR Fallback",    "Use OCR when vision model is unavailable"),
    ("GLANCE_JOURNAL",      "Journal Logging", "Log all interactions to the session journal"),
]


class SettingsPage(BasePage):
    title = "Settings"
    icon = "⚙"
    subtitle = "Configure Glance behavior and preferences."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[str, SettingRow] = {}

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # ── Hotkey ─────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Hotkey"))
        hotkey_card = Card()
        hk_row = QHBoxLayout()

        hk_lbl = QLabel("Global hotkey:")
        hk_lbl.setFont(dt.FONT_BODY)
        hk_lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        hk_row.addWidget(hk_lbl)

        current = getattr(self._cfg, "hotkey", "<ctrl>+<shift>+g") if self._cfg \
            else "<ctrl>+<shift>+g"
        self._hotkey_input = QLineEdit(current)
        self._hotkey_input.setStyleSheet(f"""
            QLineEdit {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: {dt.INPUT_RADIUS}px;
                padding: 6px 10px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {dt.BRAND_INDIGO.name()}; }}
        """)
        self._hotkey_input.setFixedWidth(240)
        hk_row.addWidget(self._hotkey_input)

        save_hk = FlatButton("Save")
        save_hk.clicked.connect(self._save_hotkey)
        hk_row.addWidget(save_hk)
        hk_row.addStretch()
        hotkey_card.add_layout(hk_row)
        self.body_layout.addWidget(hotkey_card)

        self.body_layout.addWidget(self.hint_label(
            "Format: <ctrl>+<shift>+g — uses pynput key notation. "
            "Changes take effect on next launch."
        ))

        # ── Feature Toggles ────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Features"))

        for env_key, label, desc in _TOGGLES:
            current = os.environ.get(env_key, "0").strip()
            checked = current in ("1", "true", "yes")
            row = SettingRow(label, desc, checked=checked)
            row.toggled.connect(lambda on, ek=env_key: self._toggle(ek, on))
            self._rows[env_key] = row
            self.body_layout.addWidget(row)

        self.body_layout.addStretch()

    def _save_hotkey(self):
        if not self._cfg:
            return
        val = self._hotkey_input.text().strip()
        if val:
            self._cfg._persist_env("GLANCE_HOTKEY", val)
            self._cfg.hotkey = val

    def _toggle(self, env_key: str, on: bool):
        if not self._cfg:
            return
        self._cfg._persist_env(env_key, "1" if on else "0")
        os.environ[env_key] = "1" if on else "0"

    def on_activate(self):
        for env_key, _label, _desc in _TOGGLES:
            row = self._rows.get(env_key)
            if row:
                current = os.environ.get(env_key, "0").strip()
                row.switch.set_checked(current in ("1", "true", "yes"),
                                       animate=False)
        if self._cfg:
            self._hotkey_input.setText(
                getattr(self._cfg, "hotkey", "<ctrl>+<shift>+g")
            )
