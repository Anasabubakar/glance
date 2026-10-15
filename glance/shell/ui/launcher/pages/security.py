"""
Credentials — which keys are saved (never shown in full) and where Glance stores
things on this computer.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Banner, Card, Divider, FlatButton, GhostButton, PillBadge, StatusDot

_KEYS = [
    ("Anthropic (Claude)", "anthropic_api_key"), ("OpenAI", "openai_api_key"),
    ("Google (Gemini)", "google_api_key"), ("Deepgram", "deepgram_api_key"),
    ("ElevenLabs", "elevenlabs_api_key"), ("Tavily", "tavily_api_key"),
]


def _user_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Glance"


def _open(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(path))                      # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def elide_middle(text: str, n: int = 46) -> str:
    return text if len(text) <= n else text[: n // 2 - 1] + "…" + text[-(n // 2):]


class SecurityPage(BasePage):
    title = "Credentials"
    icon = "shield"
    subtitle = "Which keys are saved, and where Glance keeps its files."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        self.body_layout.addWidget(Banner(
            "Keys stay on this computer, in your user folder. Glance only ever sends a key to the service "
            "it belongs to, and never shows one in full.", "info"))

        self.body_layout.addWidget(self.section_label("Saved keys"))
        card = Card(padding=8)
        card._layout.setSpacing(0)
        self._rows: dict[str, tuple] = {}
        for i, (label, attr) in enumerate(_KEYS):
            if i:
                card.add_widget(Divider())
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(10)
            dot = StatusDot(dt.TEXT_DIM)
            rl.addWidget(dot)
            n = QLabel(label)
            n.setFont(dt.font(14, dt.QFont.Weight.Medium))
            rl.addWidget(n, 1)
            tail = QLabel("")
            tail.setFont(dt.FONT_MONO)
            tail.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
            rl.addWidget(tail)
            pill = PillBadge("Not set", "default")
            rl.addWidget(pill)
            card.add_widget(row)
            self._rows[attr] = (dot, tail, pill)
        self.body_layout.addWidget(card)

        self.body_layout.addWidget(self.section_label("Where things are stored"))
        loc = Card(padding=20)
        loc._layout.setSpacing(14)
        user = _user_dir()
        for label, path in (("Your data folder", user), ("Saved settings file", user / ".env"),
                            ("Activity log", Path.home() / ".glance" / "logs")):
            row = QHBoxLayout()
            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(label)
            t.setFont(dt.font(14, dt.QFont.Weight.Medium))
            col.addWidget(t)
            p = QLabel(elide_middle(str(path)))
            p.setFont(dt.FONT_MONO)
            p.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            p.setToolTip(str(path))
            col.addWidget(p)
            row.addLayout(col, 1)
            b = FlatButton("Open", icon="external")
            target = path if path.suffix == "" else path.parent
            b.clicked.connect(lambda _c=False, d=target: _open(d))
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
            loc.add_layout(row)
        self.body_layout.addWidget(loc)
        self.body_layout.addStretch()

    def on_activate(self):
        if not self._cfg:
            return
        for _label, attr in _KEYS:
            dot, tail, pill = self._rows[attr]
            val = getattr(self._cfg, attr, "") or ""
            if val:
                dot.set_color(dt.SUCCESS)
                tail.setText("••••" + val[-4:] if len(val) > 8 else "••••")      # last 4 only
                pill.set_state("Saved", "success")
            else:
                dot.set_color(dt.TEXT_DIM)
                tail.setText("")
                pill.set_state("Not set", "default")
