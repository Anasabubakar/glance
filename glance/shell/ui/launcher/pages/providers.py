"""AI Providers page — provider priority, active switching, endpoint config."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, FlatButton, GradientButton, StatusDot
from .. import design_tokens as dt


class _HealthWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        try:
            from config import cfg
            data["active"] = cfg.llm_provider()
            data["available"] = cfg.available_llm_providers()
        except Exception:
            data["active"] = None
            data["available"] = []
        try:
            from ai.ollama_bootstrap import is_ollama_running
            data["ollama_running"] = is_ollama_running()
        except Exception:
            data["ollama_running"] = False
        self.result.emit(data)


class ProvidersPage(BasePage):
    title = "AI Providers"
    icon = "⚙"
    subtitle = "View available providers and switch the active language model backend."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []
        self._provider_widgets: dict[str, dict] = {}

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        self.body_layout.addWidget(self.section_label("Provider Priority"))
        self.body_layout.addWidget(self.hint_label(
            "Glance tries providers in order: Claude → OpenAI → GitHub Copilot → Gemini → Ollama. "
            "The first one with a valid key becomes active."
        ))

        providers = [
            ("anthropic", "Claude (Anthropic)", "Cloud LLM — best quality"),
            ("openai",    "OpenAI",             "Cloud LLM — GPT models"),
            ("copilot",   "GitHub Copilot",     "Cloud LLM — device-flow login"),
            ("gemini",    "Gemini (Google)",     "Cloud LLM — Gemini models"),
            ("ollama",    "Ollama",             "Local LLM — runs on your machine"),
        ]

        for key, name, desc in providers:
            card = Card()
            row = QHBoxLayout()

            dot = StatusDot(dt.TEXT_DIM)
            row.addWidget(dot)

            info = QVBoxLayout()
            info.setSpacing(2)
            lbl = QLabel(name)
            lbl.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            info.addWidget(lbl)
            d = QLabel(desc)
            d.setFont(dt.FONT_CAPTION)
            d.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            info.addWidget(d)
            row.addLayout(info, 1)

            status_lbl = QLabel("")
            status_lbl.setFont(dt.FONT_CAPTION)
            status_lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            row.addWidget(status_lbl)

            switch_btn = FlatButton("Activate")
            switch_btn.setFixedWidth(90)
            switch_btn.clicked.connect(lambda _c=False, k=key: self._switch_provider(k))
            row.addWidget(switch_btn)

            card.add_layout(row)
            self.body_layout.addWidget(card)

            self._provider_widgets[key] = {
                "dot": dot,
                "status": status_lbl,
                "btn": switch_btn,
            }

        self.body_layout.addStretch()

    def on_activate(self):
        w = _HealthWorker()
        w.result.connect(self._apply_data)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply_data(self, data: dict):
        active = data.get("active")
        available = data.get("available", [])
        ollama_running = data.get("ollama_running", False)

        for key, widgets in self._provider_widgets.items():
            is_available = key in available
            is_active = (key == active)

            if key == "ollama":
                is_available = ollama_running

            if is_active:
                widgets["dot"].set_color(dt.SUCCESS)
                widgets["status"].setText("Active")
                widgets["status"].setStyleSheet(f"color: {dt.SUCCESS.name()};")
                widgets["btn"].setText("Active")
                widgets["btn"].setEnabled(False)
            elif is_available:
                widgets["dot"].set_color(dt.BRAND_INDIGO)
                widgets["status"].setText("Available")
                widgets["status"].setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")
                widgets["btn"].setText("Activate")
                widgets["btn"].setEnabled(True)
            else:
                widgets["dot"].set_color(dt.TEXT_DIM)
                widgets["status"].setText("No key")
                widgets["status"].setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
                widgets["btn"].setText("Activate")
                widgets["btn"].setEnabled(False)

    def _switch_provider(self, key: str):
        if not self._cfg:
            return
        self._cfg.set_active_llm(key)
        self.on_activate()
