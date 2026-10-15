"""
Models — pick the model Glance uses (or leave it on Automatic).

One card per cloud provider listing its models by readable name, with a Vision
badge, the real default highlighted and a one-click "Use". Needs the provider's
key (added under AI & Keys) to list models.
"""

from __future__ import annotations

import re
import threading

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Banner, Card, Divider, FlatButton, GhostButton, PillBadge

MODEL_PROVIDERS = [
    ("claude", "Claude", "anthropic_api_key"),
    ("openai", "OpenAI", "openai_api_key"),
    ("gemini", "Google Gemini", "google_api_key"),
]
_NOT_CHAT = re.compile(r"image|tts|audio|live|embed|robotics|computer-use|imagen|veo|nano|omni|"
                       r"antigravity|gemma|learnlm|aqa", re.I)
_SHOW = 10


class _ModelLoader(QObject):
    result = pyqtSignal(str, list)

    def __init__(self, provider: str, force: bool = False):
        super().__init__()
        self.provider, self.force = provider, force

    def run(self):
        models = []
        try:
            if self.force:
                from ai.model_registry import refresh
                refresh(self.provider)
            from ai.model_registry import cached_models
            models = cached_models(self.provider) or []
        except Exception:
            pass
        self.result.emit(self.provider, models)


def _norm(m) -> dict:
    """Registry entries are dicts {id,label,vision}; tolerate plain strings."""
    if isinstance(m, dict):
        mid = str(m.get("id", ""))
        return {"id": mid, "label": str(m.get("label") or mid), "vision": bool(m.get("vision", True))}
    return {"id": str(m), "label": str(m), "vision": True}


class _ProviderModels(Card):
    def __init__(self, page: "ModelsPage", key: str, name: str):
        super().__init__(padding=18)
        self.page, self.key, self.name = page, key, name
        self._layout.setSpacing(0)
        self._expanded = False
        self._models: list = []

    def render(self, models: list, has_key: bool, active_provider: str, active_model):
        self.clear_layout()
        self._models = [_norm(m) for m in models if not (self.key == "gemini" and _NOT_CHAT.search(str(_norm(m)["id"])))]
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 10)
        t = QLabel(self.name)
        t.setFont(dt.font(15, dt.QFont.Weight.DemiBold))
        head.addWidget(t)
        if has_key:
            head.addWidget(PillBadge(f"{len(self._models)} models", "default"))
        head.addStretch()
        if has_key:
            r = GhostButton("Refresh", icon="refresh")
            r.clicked.connect(lambda: self.page.load(self.key, force=True))
            head.addWidget(r)
        w = QWidget()
        w.setLayout(head)
        self._layout.addWidget(w)

        if not has_key:
            go = FlatButton("Add a key")
            go.clicked.connect(lambda: self.page.goto("api_keys"))
            self._layout.addWidget(Banner(f"Add your {self.name} key under AI & Keys to see its models.",
                                          "info", go))
            return
        if not self._models:
            self._layout.addWidget(self.page.hint_label("No models found. Check the key, then press Refresh."))
            return

        shown = self._models if self._expanded else self._models[:_SHOW]
        for i, m in enumerate(shown):
            if i:
                self._layout.addWidget(Divider())
            is_default = (self.key == active_provider and m["id"] == active_model)
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 11, 0, 11)
            rl.setSpacing(12)
            col = QVBoxLayout()
            col.setSpacing(1)
            name = QLabel(m["label"])
            name.setFont(dt.font(14, dt.QFont.Weight.Medium))
            col.addWidget(name)
            mid = QLabel(m["id"])
            mid.setFont(dt.FONT_MONO)
            mid.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
            col.addWidget(mid)
            rl.addLayout(col, 1)
            rl.addWidget(PillBadge("Vision" if m["vision"] else "Text only", "info" if m["vision"] else "default"))
            if is_default:
                rl.addWidget(PillBadge("Default", "accent"))
            else:
                b = FlatButton("Use")
                b.setFixedWidth(72)
                b.clicked.connect(lambda _c=False, mid=m["id"]: self.page.use(self.key, mid))
                rl.addWidget(b)
            self._layout.addWidget(row)
        if len(self._models) > _SHOW:
            more = GhostButton("Show fewer" if self._expanded else f"Show all {len(self._models)}")
            more.clicked.connect(self._toggle)
            self._layout.addWidget(more, 0, Qt.AlignmentFlag.AlignLeft)

    def _toggle(self):
        self._expanded = not self._expanded
        self.page.render_all()


class ModelsPage(BasePage):
    title = "Models"
    icon = "ai"
    subtitle = "Choose the model Glance uses, or leave it on Automatic."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None
        self._data: dict[str, list] = {}
        self._workers: list = []

        # Automatic
        self._auto = Card(padding=18)
        self.body_layout.addWidget(self._auto)

        self._cards: dict[str, _ProviderModels] = {}
        for key, name, _attr in MODEL_PROVIDERS:
            c = _ProviderModels(self, key, name)
            self._cards[key] = c
            self.body_layout.addWidget(c)
        self.body_layout.addWidget(self.hint_label("Model lists are cached for 30 days. Press Refresh for the latest."))
        self.body_layout.addStretch()
        self.render_all()

    def goto(self, key: str):
        win = self.window()
        if hasattr(win, "_navigate"):
            win._navigate(key)

    def on_activate(self):
        for key, _n, _a in MODEL_PROVIDERS:
            if getattr(self._cfg, _a, None):
                self.load(key)
        self.render_all()

    def load(self, provider: str, force: bool = False):
        w = _ModelLoader(provider, force)
        w.result.connect(self._on_loaded)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _on_loaded(self, provider: str, models: list):
        self._data[provider] = models
        self.render_all()

    def render_all(self):
        c = self._cfg
        active_provider = c.llm_provider() if c else ""
        active_model = c.active_model() if c else None
        # automatic card
        self._auto.clear_layout()
        row = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Automatic")
        t.setFont(dt.font(15, dt.QFont.Weight.DemiBold))
        col.addWidget(t)
        col.addWidget(self.hint_label("Glance picks a good, available model for you and switches if one is "
                                      "busy or retired. Recommended."))
        row.addLayout(col, 1)
        if active_model is None:
            row.addWidget(PillBadge("In use", "accent"))
        else:
            b = FlatButton("Use Automatic")
            b.clicked.connect(self.use_auto)
            row.addWidget(b)
        self._auto.add_layout(row)
        for key, _name, attr in MODEL_PROVIDERS:
            has = bool(getattr(c, attr, None)) if c else False
            self._cards[key].render(self._data.get(key, []), has, active_provider, active_model)

    def use(self, provider: str, model_id: str):
        if self._cfg:
            self._cfg.set_active_llm(provider)      # also clears any stale model override
            self._cfg.set_active_model(model_id)
        self.render_all()

    def use_auto(self):
        if self._cfg:
            self._cfg.set_active_model("")
        self.render_all()
