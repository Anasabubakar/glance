"""
Home page — premium dashboard with launch button, provider status, health, activity.
"""

from __future__ import annotations

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, GradientButton, StatusDot, FlatButton, StatCard
from .. import design_tokens as dt
from ..widgets import PillBadge


class _HomeWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        try:
            from config import cfg
            data["llm"] = cfg.llm_provider()
            data["stt"] = cfg.stt_provider()
            data["tts"] = cfg.tts_provider()
            data["search"] = cfg.search_provider()
            data["describe"] = cfg.describe()
        except Exception:
            pass
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
                data["recent_log"] = lines[-15:]
            else:
                data["recent_log"] = []
        except Exception:
            data["recent_log"] = []
        self.result.emit(data)


class HomePage(BasePage):
    title = "Dashboard"
    icon = "⏎"
    subtitle = "Launch Glance and monitor system status at a glance."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._companion_running = False

        # ── Launch Button ───────────────────────────────────────────────
        launch_row = QHBoxLayout()
        self._launch_btn = GradientButton("Start Glance")
        self._launch_btn.setFixedHeight(56)
        self._launch_btn.setFont(dt.font(16, dt.QFont.Weight.Bold))
        self._launch_btn.clicked.connect(self._on_launch)
        launch_row.addWidget(self._launch_btn)

        self._status_badge = PillBadge("Not Running", "default")
        launch_row.addWidget(self._status_badge)
        self.body_layout.addLayout(launch_row)

        # ── Provider Status Grid ────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Active Providers"))
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(12)
        self._provider_cards = {}

        providers = [
            ("llm", "Language Model"),
            ("stt", "Speech-to-Text"),
            ("tts", "Text-to-Speech"),
            ("search", "Web Search"),
        ]
        for i, (key, label) in enumerate(providers):
            sc = StatCard(label)
            self._provider_cards[key] = sc
            self._cards_grid.addWidget(sc, 0, i)
        self.body_layout.addLayout(self._cards_grid)

        # ─── Health Section ─────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("System Health"))
        health_card = Card()

        # Ollama
        ollama_row = QHBoxLayout()
        self._ollama_dot = StatusDot(dt.TEXT_DIM)
        ollama_row.addWidget(self._ollama_dot)
        self._ollama_label = QLabel("Ollama: checking…")
        self._ollama_label.setFont(dt.FONT_BODY)
        self._ollama_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        ollama_row.addWidget(self._ollama_label, 1)

        self._ollama_model_lbl = QLabel("")
        self._ollama_model_lbl.setFont(dt.FONT_CAPTION)
        self._ollama_model_lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        ollama_row.addWidget(self._ollama_model_lbl)
        health_card.add_layout(ollama_row)

        # Provider connection check
        prov_row = QHBoxLayout()
        self._prov_dot = StatusDot(dt.TEXT_DIM)
        prov_row.addWidget(self._prov_dot)
        prov_text = QLabel("Active LLM provider:")
        prov_text.setFont(dt.FONT_BODY)
        prov_text.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        prov_row.addWidget(prov_text)
        self._prov_label = QLabel("none")
        self._prov_label.setFont(dt.font(13, dt.QFont.Weight.DemiBold))
        self._prov_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        prov_row.addWidget(self._prov_label, 1)
        health_card.add_layout(prov_row)

        self.body_layout.addWidget(health_card)

        # ── Recent Activity ─────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Recent Activity"))
        activity_card = Card()
        self._log_label = QLabel("No recent activity.")
        self._log_label.setFont(dt.FONT_MONO)
        self._log_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._log_label.setWordWrap(True)
        self._log_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        activity_card.add_widget(self._log_label)
        self.body_layout.addWidget(activity_card)

        self.body_layout.addStretch()

    def on_activate(self):
        w = _HomeWorker()
        w.result.connect(self._apply_data)
        self._worker = w
        threading.Thread(target=w.run, daemon=True).start()

    def _apply_data(self, data: dict):
        # Provider status cards
        for key in ("llm", "stt", "tts", "search"):
            sc = self._provider_cards.get(key)
            if sc:
                provider = data.get(key) or "none"
                display = str(provider).replace("_", " ").title()
                is_ok = provider and provider != "none"
                sc.set_value(display, dt.SUCCESS if is_ok else dt.TEXT_DIM)

        # Ollama health
        running = data.get("ollama_running", False)
        self._ollama_dot.set_color(dt.SUCCESS if running else dt.WARNING)
        self._ollama_label.setText(
            f"Ollama: {'Running' if running else 'Not running'}"
        )
        self._ollama_label.setStyleSheet(
            f"color: {dt.SUCCESS.name() if running else dt.WARNING.name()};"
        )
        if running:
            self._ollama_model_lbl.setText("Local inference ready")

        # Provider connection
        llm = data.get("llm") or "none"
        if llm and llm != "none":
            self._prov_dot.set_color(dt.SUCCESS)
            self._prov_label.setText(str(llm).title())
        else:
            self._prov_dot.set_color(dt.TEXT_DIM)
            self._prov_label.setText("No provider configured")

        # Recent log
        lines = data.get("recent_log", [])
        if lines:
            text = "\n".join(lines)
            self._log_label.setText(text)
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
            self._status_badge.setText("Running")
            self._status_badge.setStyleSheet(
                "background: rgba(74,222,128,0.1); color: #4ADE80; "
                "border: 1px solid rgba(74,222,128,0.2); "
                "border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 500;"
            )
        else:
            self._launch_btn.setText("Start Glance")
            self._launch_btn.setEnabled(True)
            self._status_badge.setText("Not Running")
