"""Security page — credential audit, .env file locations, key status."""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt
import subprocess

from ..page_base import BasePage
from ..widgets import Card, FlatButton, StatusDot
from .. import design_tokens as dt

_KEYS = [
    ("ANTHROPIC_API_KEY",  "Anthropic",  "anthropic_api_key"),
    ("OPENAI_API_KEY",     "OpenAI",     "openai_api_key"),
    ("GOOGLE_API_KEY",     "Gemini",     "google_api_key"),
    ("DEEPGRAM_API_KEY",   "Deepgram",   "deepgram_api_key"),
    ("ELEVENLABS_API_KEY", "ElevenLabs", "elevenlabs_api_key"),
    ("TAVILY_API_KEY",     "Tavily",     "tavily_api_key"),
]


class SecurityPage(BasePage):
    title = "Security"
    icon = "\U0001F512"
    subtitle = "Credential inventory and .env file locations."

    def __init__(self, parent=None):
        super().__init__(parent)

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # Credential audit
        self.body_layout.addWidget(self.section_label("Credential Inventory"))
        self._key_widgets: dict[str, tuple[StatusDot, QLabel]] = {}

        for env_key, label, attr in _KEYS:
            card = Card()
            row = QHBoxLayout()
            dot = StatusDot(dt.TEXT_DIM)
            row.addWidget(dot)
            name = QLabel(label)
            name.setFont(dt.FONT_BODY)
            name.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(name, 1)
            status = QLabel("—")
            status.setFont(dt.FONT_CAPTION)
            row.addWidget(status)
            card.add_layout(row)
            self.body_layout.addWidget(card)
            self._key_widgets[attr] = (dot, status)

        # .env locations
        self.body_layout.addWidget(self.section_label("Storage Locations"))
        loc_card = Card()

        frozen = getattr(sys, "frozen", False)
        here = Path(__file__).parent
        if sys.platform == "win32":
            user_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
        else:
            user_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Glance"
        user_env = user_dir / ".env"
        writable_env = user_env if frozen else (here.parents[3] / "shell" / ".env")

        for label, path in [
            ("User data directory", str(user_dir)),
            ("User .env", str(user_env)),
            ("Writable .env", str(writable_env)),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setFont(dt.FONT_BODY)
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(lbl)
            val = QLabel(path)
            val.setFont(dt.FONT_CAPTION)
            val.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(val, 1)
            loc_card.add_layout(row)

        reveal_btn = FlatButton("Open Data Directory")
        reveal_btn.clicked.connect(lambda: self._open_dir(user_dir))
        loc_card.add_widget(reveal_btn)
        self.body_layout.addWidget(loc_card)

        self.body_layout.addStretch()

    def on_activate(self):
        if not self._cfg:
            return
        for _env_key, _label, attr in _KEYS:
            dot, status = self._key_widgets.get(attr, (None, None))
            if not dot or not status:
                continue
            val = getattr(self._cfg, attr, "") or ""
            if val:
                dot.set_color(dt.SUCCESS)
                masked = val[:4] + "•" * max(0, len(val) - 8) + val[-4:] if len(val) > 8 else "••••"
                status.setText(f"Set: {masked}")
                status.setStyleSheet(f"color: {dt.SUCCESS.name()};")
            else:
                dot.set_color(dt.TEXT_DIM)
                status.setText("Not set")
                status.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")

    def _open_dir(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
