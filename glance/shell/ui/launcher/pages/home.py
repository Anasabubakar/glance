"""Home page — launch button, status cards, health indicators, recent log."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, GradientButton, StatusDot, FlatButton
from .. import design_tokens as dt


class _Worker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        try:
            from config import cfg
            data["describe"] = cfg.describe()
            data["llm"] = cfg.llm_provider()
            data["stt"] = cfg.stt_provider()
            data["tts"] = cfg.tts_provider()
            data["search"] = cfg.search_provider()
        except Exception:
            data["describe"] = {}
        try:
            from ai.ollama_bootstrap import is_ollama_running
            data["ollama_running"] = is_ollama_running()
        except Exception:
            data["ollama_running"] = False
        try:
            from pathlib import Path
            log_path = Path.home() / ".glance" / "logs" / "session.log"
            if log_path.exists():
                lines = log_path.read_text(errors="replace").strip().splitlines()
                data["recent_log"] = lines[-10:]
            else:
                data["recent_log"] = []
        except Exception:
            data["recent_log"] = []
        self.result.emit(data)


class HomePage(BasePage):
    title = "Home"
    icon = "⌂"
    subtitle = "Launch Glance and view system status at a glance."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._companion_running = False

        # Launch button
        self._launch_btn = GradientButton("Start Glance")
        self._launch_btn.setFixedHeight(52)
        self._launch_btn.clicked.connect(self._on_launch)
        self.body_layout.addWidget(self._launch_btn)

        # Status cards row
        self.body_layout.addWidget(self.section_label("Active Providers"))
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(12)
        self._provider_cards = {}
        for i, (key, label) in enumerate([
            ("llm", "Language Model"),
            ("stt", "Speech-to-Text"),
            ("tts", "Text-to-Speech"),
            ("search", "Web Search"),
        ]):
            card = Card()
            title = QLabel(label)
            title.setFont(dt.FONT_CAPTION)
            title.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            card.add_widget(title)
            val = QLabel("—")
            val.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            val.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            card.add_widget(val)
            self._provider_cards[key] = val
            self._cards_grid.addWidget(card, 0, i)
        self.body_layout.addLayout(self._cards_grid)

        # Health
        self.body_layout.addWidget(self.section_label("Health"))
        health_row = QHBoxLayout()
        self._ollama_dot = StatusDot(dt.TEXT_DIM)
        health_row.addWidget(self._ollama_dot)
        self._ollama_label = QLabel("Ollama: checking…")
        self._ollama_label.setFont(dt.FONT_BODY)
        self._ollama_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        health_row.addWidget(self._ollama_label)
        health_row.addStretch()
        self.body_layout.addLayout(health_row)

        # Recent activity
        self.body_layout.addWidget(self.section_label("Recent Activity"))
        self._log_label = QLabel("Loading…")
        self._log_label.setFont(dt.FONT_MONO)
        self._log_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._log_label.setWordWrap(True)
        self._log_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.body_layout.addWidget(self._log_label)

        self.body_layout.addStretch()

    def on_activate(self):
        w = _Worker()
        w.result.connect(self._apply_data)
        self._worker = w
        threading.Thread(target=w.run, daemon=True).start()

    def _apply_data(self, data: dict):
        desc = data.get("describe", {})
        for key in ("llm", "stt", "tts", "search"):
            lbl = self._provider_cards.get(key)
            if lbl:
                provider = data.get(key) or "none"
                lbl.setText(str(provider).replace("_", " ").title())

        running = data.get("ollama_running", False)
        self._ollama_dot.set_color(dt.SUCCESS if running else dt.ERROR)
        self._ollama_label.setText(f"Ollama: {'running' if running else 'stopped'}")

        lines = data.get("recent_log", [])
        if lines:
            self._log_label.setText("\n".join(lines))
        else:
            self._log_label.setText("No recent activity.")

    def _on_launch(self):
        win = self.window()
        if hasattr(win, "start_companion"):
            win.start_companion()

    def set_companion_running(self, running: bool):
        self._companion_running = running
        if running:
            self._launch_btn.setText("Glance is Running")
            self._launch_btn.setEnabled(False)
        else:
            self._launch_btn.setText("Start Glance")
            self._launch_btn.setEnabled(True)
