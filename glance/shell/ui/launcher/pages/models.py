"""
Models page — per-provider model lists, defaults, refresh.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import pyqtSignal, QObject

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


MODEL_PROVIDERS = [
    ("claude", "Claude (Anthropic)"),
    ("openai", "OpenAI"),
    ("gemini", "Gemini (Google)"),
]


class ModelsPage(BasePage):
    title = "Models"
    icon = "🧠"
    subtitle = "View and select default models for each provider."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []
        self._model_cards: dict[str, Card] = {}
        self._current_labels: dict[str, QLabel] = {}

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        for pkey, pname in MODEL_PROVIDERS:
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
            refresh_btn.clicked.connect(
                lambda _c=False, k=pkey: self._refresh(k)
            )
            header.addWidget(refresh_btn)
            card.add_layout(header)

            loading = QLabel("Loading models…")
            loading.setFont(dt.FONT_CAPTION)
            loading.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            card.add_widget(loading)

            self._model_cards[pkey] = card
            self.body_layout.addWidget(card)

        self.body_layout.addWidget(self.hint_label(
            "Models are cached for 30 days. Click Refresh to fetch the latest list."
        ))
        self.body_layout.addStretch()

    def on_activate(self):
        for pkey, _pname in MODEL_PROVIDERS:
            self._load(pkey)

    def _load(self, provider: str):
        card = self._model_cards.get(provider)
        if card:
            loading = QLabel("Loading models…")
            loading.setFont(dt.FONT_CAPTION)
            loading.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            card.clear_layout()
            card.add_widget(loading)

        w = _ModelLoader(provider)
        w.result.connect(self._apply)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _refresh(self, provider: str):
        def _do():
            try:
                from ai.model_registry import refresh
                refresh(provider)
            except Exception:
                pass
            self._load(provider)

        threading.Thread(target=_do, daemon=True).start()

    def _apply(self, provider: str, models: list):
        card = self._model_cards.get(provider)
        if not card:
            return
        card.clear_layout()

        # Re-add header
        for pkey, pname in MODEL_PROVIDERS:
            if pkey == provider:
                header = QHBoxLayout()
                title = QLabel(pname)
                title.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
                title.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
                header.addWidget(title)
                header.addStretch()
                current = self._current_labels.get(provider, QLabel(""))
                header.addWidget(current)
                refresh_btn = FlatButton("Refresh")
                refresh_btn.setFixedWidth(80)
                refresh_btn.clicked.connect(
                    lambda _c=False, k=provider: self._refresh(k)
                )
                header.addWidget(refresh_btn)
                card.add_layout(header)
                break

        if not models:
            lbl = QLabel("No models found. Check your API key or click Refresh.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            card.add_widget(lbl)
            return

        active_model = self._cfg.active_model() if self._cfg else None
        current_lbl = self._current_labels.get(provider)

        for model in models[:20]:
            model_id = model if isinstance(model, str) else str(model)
            row = QHBoxLayout()

            dot = StatusDot(
                dt.SUCCESS if model_id == active_model else dt.TEXT_DIM
            )
            row.addWidget(dot)

            lbl = QLabel(model_id)
            lbl.setFont(dt.font(12))
            lbl.setStyleSheet(
                f"color: {dt.BRAND_INDIGO.name() if model_id == active_model else dt.TEXT_PRIMARY.name()};"
            )
            row.addWidget(lbl, 1)

            if model_id == active_model:
                tag = QLabel("default")
                tag.setFont(dt.FONT_SMALL)
                tag.setStyleSheet(f"color: {dt.SUCCESS.name()};")
                row.addWidget(tag)
                if current_lbl:
                    current_lbl.setText(f"Default: {model_id}")

            select_btn = FlatButton("Select")
            select_btn.setFixedWidth(70)
            select_btn.clicked.connect(
                lambda _c=False, mid=model_id: self._set_default(mid)
            )
            row.addWidget(select_btn)

            w = QWidget()
            w.setLayout(row)
            card.add_widget(w)

    def _set_default(self, model_id: str):
        if self._cfg:
            self._cfg.set_active_model(model_id)
        for pkey, _pname in MODEL_PROVIDERS:
            self._load(pkey)
