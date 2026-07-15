"""Models page — per-provider model lists, defaults, refresh."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QButtonGroup, QScrollArea, QFrame,
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton, StatusDot
from .. import design_tokens as dt


class _ModelLoader(QObject):
    result = pyqtSignal(str, list)

    def __init__(self, provider: str):
        super().__init__()
        self.provider = provider

    def run(self):
        models = []
        try:
            from ai.model_registry import cached_models
            models = cached_models(self.provider) or []
        except Exception:
            pass
        self.result.emit(self.provider, models)


class ModelsPage(BasePage):
    title = "Models"
    icon = "\U0001F9E0"
    subtitle = "View and select default models for each provider."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []
        self._model_containers: dict[str, QVBoxLayout] = {}
        self._current_labels: dict[str, QLabel] = {}

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        self._providers = [
            ("anthropic", "Claude"),
            ("openai", "OpenAI"),
            ("gemini", "Gemini"),
        ]

        for pkey, pname in self._providers:
            card = Card()
            header = QHBoxLayout()
            title = QLabel(pname)
            title.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            title.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            header.addWidget(title)
            header.addStretch()

            current = QLabel("—")
            current.setFont(dt.FONT_CAPTION)
            current.setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")
            header.addWidget(current)
            self._current_labels[pkey] = current

            refresh_btn = FlatButton("Refresh")
            refresh_btn.setFixedWidth(80)
            refresh_btn.clicked.connect(lambda _c=False, k=pkey: self._refresh_provider(k))
            header.addWidget(refresh_btn)

            card.add_layout(header)

            model_list = QVBoxLayout()
            model_list.setSpacing(4)
            loading = QLabel("Loading models…")
            loading.setFont(dt.FONT_CAPTION)
            loading.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            model_list.addWidget(loading)
            card.add_layout(model_list)
            self._model_containers[pkey] = model_list

            self.body_layout.addWidget(card)

        self.body_layout.addWidget(self.hint_label(
            "Models are cached for 30 days. Click Refresh to fetch the latest list from the provider."
        ))
        self.body_layout.addStretch()

    def on_activate(self):
        for pkey, _pname in self._providers:
            self._load_models(pkey)

    def _load_models(self, provider: str):
        w = _ModelLoader(provider)
        w.result.connect(self._apply_models)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _refresh_provider(self, provider: str):
        def _do_refresh():
            try:
                from ai.model_registry import refresh
                refresh(provider)
            except Exception:
                pass
            self._load_models(provider)
        threading.Thread(target=_do_refresh, daemon=True).start()

    def _apply_models(self, provider: str, models: list):
        container = self._model_containers.get(provider)
        if not container:
            return

        while container.count():
            item = container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not models:
            lbl = QLabel("No models found. Check your API key or click Refresh.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            container.addWidget(lbl)
            return

        active_model = None
        if self._cfg:
            active_model = getattr(self._cfg, "active_model", None)

        current_label = self._current_labels.get(provider)

        for model in models[:20]:
            model_id = model if isinstance(model, str) else getattr(model, "id", str(model))
            row = QHBoxLayout()
            btn = FlatButton(model_id)
            btn.setStyleSheet(btn.styleSheet() + "text-align: left; padding-left: 12px;")
            if model_id == active_model:
                btn.setStyleSheet(btn.styleSheet().replace(
                    dt.BG_ELEVATED.name(), "rgba(100,107,242,0.15)"
                ))
                if current_label:
                    current_label.setText(f"Default: {model_id}")
            btn.clicked.connect(lambda _c=False, mid=model_id: self._set_default(mid, provider))
            row.addWidget(btn, 1)

            w = QWidget()
            w.setLayout(row)
            container.addWidget(w)

    def _set_default(self, model_id: str, provider: str):
        if self._cfg:
            self._cfg.set_active_model(model_id)
        self._load_models(provider)
