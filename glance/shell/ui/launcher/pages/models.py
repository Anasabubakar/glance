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
    ("groq", "Groq", "groq_api_key"),
    ("openrouter", "OpenRouter: free models", "openrouter_api_key"),
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
            import asyncio
            from ai.model_registry import cache_is_stale, refresh
            import os as _os
            if (self.force or cache_is_stale(self.provider)) and not _os.environ.get("PYTEST_CURRENT_TEST"):
                try:
                    asyncio.run(refresh(self.provider))      # refresh() is a coroutine
                except Exception:
                    pass
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

    def render(self, models: list, has_key: bool, active_provider: str, active_model, active_text=None):
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

        if self.key == "openrouter" and not getattr(self.page._cfg, "openrouter_api_key", None):
            go = FlatButton("Add a key")
            go.clicked.connect(lambda: self.page.goto("api_keys"))
            self._layout.addWidget(Banner("These models are free. Add your free OpenRouter key under "
                                          "AI & Keys to use them.", "info", go))
        elif not has_key:
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
            on_provider = self.key == active_provider
            is_vision = on_provider and m["id"] == active_model
            is_text = on_provider and m["id"] == active_text
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 11, 0, 11)
            rl.setSpacing(8)
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
            if self.key == "openrouter":
                rl.addWidget(PillBadge("Free", "success"))
            if not m["vision"]:
                rl.addWidget(PillBadge("Text only", "default"))
            if is_text:
                rl.addWidget(PillBadge("Text", "accent"))
            else:
                bt = GhostButton("Use for text")
                bt.clicked.connect(lambda _c=False, mid=m["id"]: self.page.use(self.key, mid, "text"))
                rl.addWidget(bt)
            if m["vision"]:
                if is_vision:
                    rl.addWidget(PillBadge("Vision", "accent"))
                else:
                    bv = FlatButton("Use for vision")
                    bv.clicked.connect(lambda _c=False, mid=m["id"]: self.page.use(self.key, mid, "vision"))
                    rl.addWidget(bv)
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
    subtitle = "Pick one model for chat (text) and another for seeing your screen (vision)."

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
            if getattr(self._cfg, _a, None) or key == "openrouter":
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
        active_text = c.text_model_pick() if c else None
        # automatic card
        self._auto.clear_layout()
        row = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Automatic")
        t.setFont(dt.font(15, dt.QFont.Weight.DemiBold))
        col.addWidget(t)
        col.addWidget(self.hint_label("Glance picks a fast, available model for chat and for vision, and switches if one is "
                                      "busy or retired. Recommended."))
        row.addLayout(col, 1)
        if active_model is None and active_text is None:
            row.addWidget(PillBadge("In use", "accent"))
        else:
            b = FlatButton("Reset both to Automatic")
            b.clicked.connect(self.use_auto)
            row.addWidget(b)
        self._auto.add_layout(row)
        for key, _name, attr in MODEL_PROVIDERS:
            has = (bool(getattr(c, attr, None)) if c else False) or key == "openrouter"
            self._cards[key].render(self._data.get(key, []), has, active_provider, active_model, active_text)

    def use(self, provider: str, model_id: str, kind: str = "vision"):
        c = self._cfg
        if c:
            if c.llm_provider() != provider:
                c.set_active_llm(provider)          # also clears stale model picks
            if kind == "text":
                c.set_text_model(model_id)
            else:
                c.set_active_model(model_id)
        self.render_all()

    def use_auto(self):
        if self._cfg:
            self._cfg.remove_env_values(["GLANCE_ACTIVE_MODEL", "GLANCE_TEXT_MODEL"])
        self.render_all()
