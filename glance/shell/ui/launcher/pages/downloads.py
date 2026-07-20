"""
Downloads page — Ollama model download tracking.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, StatusDot
from .. import design_tokens as dt


class _ModelSizeWorker(QObject):
    result = pyqtSignal(list)

    def run(self):
        models = []
        try:
            from ai.ollama_bootstrap import is_ollama_running, list_installed_models
            if is_ollama_running():
                raw = list_installed_models()
                for m in raw:
                    name = m if isinstance(m, str) else str(m)
                    models.append({"name": name, "size": None})
        except Exception:
            pass
        self.result.emit(models)


class DownloadsPage(BasePage):
    title = "Downloads"
    icon = "⬇"
    subtitle = "Track downloaded Ollama models."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []

        self.body_layout.addWidget(self.section_label("Downloaded Models"))
        self._container = QVBoxLayout()
        self._container.setSpacing(6)
        self.body_layout.addLayout(self._container)

        self.body_layout.addWidget(self.hint_label(
            "Models are downloaded when pulled via the Ollama page. "
            "Use the Ollama page to pull new models."
        ))
        self.body_layout.addStretch()

    def on_activate(self):
        while self._container.count():
            item = self._container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        loading = QLabel("Loading…")
        loading.setFont(dt.FONT_CAPTION)
        loading.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._container.addWidget(loading)

        w = _ModelSizeWorker()
        w.result.connect(self._apply)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply(self, models: list):
        while self._container.count():
            item = self._container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not models:
            lbl = QLabel("No downloaded models found. Make sure Ollama is running.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._container.addWidget(lbl)
            return

        for m in models:
            card = Card()
            row = QHBoxLayout()
            dot = StatusDot(dt.SUCCESS)
            row.addWidget(dot)
            name = QLabel(m["name"])
            name.setFont(dt.font(13, dt.QFont.Weight.DemiBold))
            name.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(name, 1)
            card.add_layout(row)
            self._container.addWidget(card)
