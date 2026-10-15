"""
Settings — how Glance listens and behaves.

Every toggle comes from prefs.py (one source of truth shared with the tray menu
and the running app), shows its real current value, and applies immediately.
"""

from __future__ import annotations

import re

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

import prefs

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Card, FlatButton, GradientButton, SettingRow, SettingsGroup

_MODS = {"ctrl", "control", "alt", "shift", "super", "win", "cmd"}


def normalize_hotkey(text: str) -> str | None:
    """'Ctrl + Alt + M' -> 'ctrl+alt+m'; None if it isn't a valid combo."""
    parts = [p for p in re.split(r"\s*\+\s*", text.strip().lower()) if p]
    if len(parts) < 2 or len(parts) > 4:
        return None
    *mods, key = parts
    if not mods or any(m not in _MODS for m in mods) or key in _MODS:
        return None
    if len(key) > 1 and key not in {"space", "enter", "tab", "esc"} and not re.fullmatch(r"f\d{1,2}", key):
        return None
    return "+".join(mods + [key])


class SettingsPage(BasePage):
    title = "Settings"
    icon = "sliders"
    subtitle = "How Glance listens and behaves. Changes apply right away."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: dict[str, SettingRow] = {}
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # ── Hotkey ──────────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Talk to Glance"))
        card = Card(padding=20)
        top = QVBoxLayout()
        top.setSpacing(3)
        t = QLabel("Push-to-talk hotkey")
        t.setFont(dt.font(14, dt.QFont.Weight.Medium))
        d = QLabel("Hold it, speak, and let go to send. Example: ctrl+alt+m")
        d.setFont(dt.FONT_CAPTION)
        d.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        top.addWidget(t)
        top.addWidget(d)
        card.add_layout(top)
        row = QHBoxLayout()
        row.setSpacing(10)
        self._hotkey = QLineEdit(getattr(self._cfg, "hotkey", "ctrl+alt+m") if self._cfg else "ctrl+alt+m")
        self._hotkey.setMaximumWidth(280)
        row.addWidget(self._hotkey)
        save = GradientButton("Save")
        save.setMinimumHeight(38)
        save.clicked.connect(self._save_hotkey)
        row.addWidget(save)
        reset = FlatButton("Reset")
        reset.clicked.connect(lambda: self._hotkey.setText("ctrl+alt+m"))
        row.addWidget(reset)
        row.addStretch()
        card.add_layout(row)
        self._hk_msg = QLabel("")
        self._hk_msg.setFont(dt.FONT_CAPTION)
        card.add_widget(self._hk_msg)
        self.body_layout.addWidget(card)

        # ── Preference groups ───────────────────────────────────────────────
        for group, items in prefs.groups():
            self.body_layout.addWidget(self.section_label(group))
            g = SettingsGroup()
            for p in items:
                r = g.add_toggle(p.label, p.desc, prefs.get(p.env))
                r.toggled.connect(lambda on, e=p.env: prefs.set_pref(e, on))
                self._rows[p.env] = r
            self.body_layout.addWidget(g)
        self.body_layout.addStretch()

    def _save_hotkey(self):
        combo = normalize_hotkey(self._hotkey.text())
        if combo is None:
            self._hk_msg.setText("That doesn't look like a hotkey. Use modifiers plus one key, like ctrl+alt+m.")
            self._hk_msg.setStyleSheet(f"color: {dt.WARNING.name()};")
            return
        self._hotkey.setText(combo)
        if self._cfg:
            self._cfg._persist_env("GLANCE_HOTKEY", combo)
            self._cfg.hotkey = combo
        self._hk_msg.setText("Saved. It takes effect the next time Glance starts.")
        self._hk_msg.setStyleSheet(f"color: {dt.SUCCESS.name()};")

    def on_activate(self):
        for env, row in self._rows.items():
            row.switch.set_checked(prefs.get(env), animate=False)
        if self._cfg:
            self._hotkey.setText(getattr(self._cfg, "hotkey", "ctrl+alt+m"))
