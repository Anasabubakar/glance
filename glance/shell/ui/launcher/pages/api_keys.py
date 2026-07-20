"""
API Keys page — per-provider key entry with validation, save/remove.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, KeyField, FlatButton, GradientButton
from .. import design_tokens as dt

_PROVIDERS = [
    ("ANTHROPIC_API_KEY",  "Anthropic (Claude)",   "anthropic_api_key"),
    ("OPENAI_API_KEY",     "OpenAI",               "openai_api_key"),
    ("GOOGLE_API_KEY",     "Google (Gemini)",       "google_api_key"),
    ("DEEPGRAM_API_KEY",   "Deepgram (STT)",       "deepgram_api_key"),
    ("ELEVENLABS_API_KEY", "ElevenLabs (TTS)",     "elevenlabs_api_key"),
    ("TAVILY_API_KEY",     "Tavily (Search)",       "tavily_api_key"),
]


class _Validator(QObject):
    finished = pyqtSignal(str, bool, str)

    def __init__(self, env_key: str, value: str):
        super().__init__()
        self.env_key = env_key
        self.value = value

    def run(self):
        ok, msg = False, "Unknown provider"
        try:
            import httpx
            if self.env_key == "ANTHROPIC_API_KEY":
                r = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": self.value, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": "claude-sonnet-4-20250514", "max_tokens": 1,
                          "messages": [{"role": "user", "content": "hi"}]},
                    timeout=15,
                )
                ok = r.status_code in (200, 400, 429)
                msg = "Valid" if ok else f"HTTP {r.status_code}"
            elif self.env_key == "OPENAI_API_KEY":
                r = httpx.get("https://api.openai.com/v1/models",
                              headers={"Authorization": f"Bearer {self.value}"},
                              timeout=15)
                ok = r.status_code == 200
                msg = "Valid" if ok else f"HTTP {r.status_code}"
            elif self.env_key == "GOOGLE_API_KEY":
                r = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.value}",
                    json={"contents": [{"parts": [{"text": "hi"}]}]},
                    timeout=15,
                )
                ok = r.status_code in (200, 400, 429)
                msg = "Valid" if ok else f"HTTP {r.status_code}"
            elif self.env_key == "DEEPGRAM_API_KEY":
                r = httpx.get("https://api.deepgram.com/v1/projects",
                              headers={"Authorization": f"Token {self.value}"},
                              timeout=15)
                ok = r.status_code == 200
                msg = "Valid" if ok else f"HTTP {r.status_code}"
            elif self.env_key == "ELEVENLABS_API_KEY":
                r = httpx.get("https://api.elevenlabs.io/v1/voices",
                              headers={"xi-api-key": self.value},
                              timeout=15)
                ok = r.status_code == 200
                msg = "Valid" if ok else f"HTTP {r.status_code}"
            elif self.env_key == "TAVILY_API_KEY":
                r = httpx.post("https://api.tavily.com/search",
                               json={"api_key": self.value, "query": "test", "max_results": 1},
                               timeout=15)
                ok = r.status_code == 200
                msg = "Valid" if ok else f"HTTP {r.status_code}"
        except Exception as e:
            msg = str(e)[:80]
        self.finished.emit(self.env_key, ok, msg)


class APIKeysPage(BasePage):
    title = "API Keys"
    icon = "🔑"
    subtitle = "Manage API keys for each provider. Keys are stored in your local .env file."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fields: dict[str, KeyField] = {}
        self._status_labels: dict[str, QLabel] = {}
        self._validators: list = []

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        for env_key, label, attr in _PROVIDERS:
            current = getattr(self._cfg, attr, "") if self._cfg else ""
            card = Card()
            field = KeyField(label, env_key, current_value=current or "")
            card.add_widget(field)

            btn_row = QHBoxLayout()
            save_btn = FlatButton("Save")
            save_btn.clicked.connect(lambda _c=False, ek=env_key: self._save_key(ek))
            btn_row.addWidget(save_btn)

            test_btn = FlatButton("Test")
            test_btn.clicked.connect(lambda _c=False, ek=env_key: self._test_key(ek))
            btn_row.addWidget(test_btn)

            remove_btn = FlatButton("Remove")
            remove_btn.clicked.connect(lambda _c=False, ek=env_key: self._remove_key(ek))
            btn_row.addWidget(remove_btn)

            btn_row.addStretch()
            status = QLabel("")
            status.setFont(dt.FONT_CAPTION)
            self._status_labels[env_key] = status
            btn_row.addWidget(status)

            card.add_layout(btn_row)
            self._fields[env_key] = field
            self.body_layout.addWidget(card)

        self.body_layout.addStretch()

    def on_activate(self):
        if not self._cfg:
            return
        for env_key, _label, attr in _PROVIDERS:
            field = self._fields.get(env_key)
            if field:
                val = getattr(self._cfg, attr, "") or ""
                field._input.setText(val)
                field._status.set_color(dt.SUCCESS if val else dt.TEXT_DIM)

    def _save_key(self, env_key: str):
        field = self._fields.get(env_key)
        if not field or not self._cfg:
            return
        value = field.get_key()
        self._cfg.save_env_values({env_key: value})
        field.set_status(bool(value))
        self._set_status(env_key, "✓ Saved", dt.SUCCESS)

    def _test_key(self, env_key: str):
        field = self._fields.get(env_key)
        if not field:
            return
        value = field.get_key()
        if not value:
            self._set_status(env_key, "No key to test", dt.WARNING)
            return
        self._set_status(env_key, "Testing…", dt.TEXT_MUTED)
        v = _Validator(env_key, value)
        v.finished.connect(self._on_validate_result)
        self._validators.append(v)
        threading.Thread(target=v.run, daemon=True).start()

    def _on_validate_result(self, env_key: str, ok: bool, msg: str):
        field = self._fields.get(env_key)
        if field:
            field.set_status(ok)
        color = dt.SUCCESS if ok else dt.ERROR
        self._set_status(env_key, msg, color)

    def _remove_key(self, env_key: str):
        field = self._fields.get(env_key)
        if not field or not self._cfg:
            return
        reply = QMessageBox.question(
            self, "Remove Key",
            f"Remove the {env_key} key? This clears it from your .env file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cfg.save_env_values({env_key: ""})
            field.clear_key()
            self._set_status(env_key, "Removed", dt.TEXT_MUTED)

    def _set_status(self, env_key: str, text: str, color):
        lbl = self._status_labels.get(env_key)
        if lbl:
            lbl.setText(text)
            lbl.setStyleSheet(f"color: {color.name()};")
