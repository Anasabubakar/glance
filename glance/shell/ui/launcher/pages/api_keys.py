"""
API Keys page — per-provider key entry with validation, save/remove.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QLineEdit,
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


class _CustomTester(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, base_url: str, key: str):
        super().__init__()
        self.base_url, self.key = base_url.rstrip("/"), key

    def run(self):
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/models", timeout=15,
                          headers={"Authorization": f"Bearer {self.key or 'none'}"})
            ok = r.status_code == 200
            self.finished.emit(ok, "Reachable" if ok else f"HTTP {r.status_code}")
        except Exception as e:
            self.finished.emit(False, str(e)[:80])


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

        self._build_custom_card()
        self.body_layout.addStretch()

    # ── Bring your own endpoint (any OpenAI-compatible server) ───────────────

    def _build_custom_card(self):
        self.body_layout.addWidget(self.section_label("Custom endpoint (BYOK)"))
        self.body_layout.addWidget(self.hint_label(
            "Use any OpenAI-compatible server: OpenRouter, Groq, Together, LM Studio, "
            "vLLM, or your own. Pick a vision-capable model to keep screen features."))
        card = Card()
        cur = self._cfg
        self._custom_url = QLineEdit(getattr(cur, "custom_base_url", "") if cur else "")
        self._custom_url.setPlaceholderText("Base URL, e.g. https://openrouter.ai/api/v1")
        self._custom_model = QLineEdit(getattr(cur, "custom_model", "") if cur else "")
        self._custom_model.setPlaceholderText("Model id, e.g. anthropic/claude-sonnet-4.5")
        self._custom_key = KeyField("API key (optional for local servers)",
                                    "GLANCE_CUSTOM_API_KEY",
                                    current_value=getattr(cur, "custom_api_key", "") if cur else "")
        for w in (self._custom_url, self._custom_model):
            card.add_widget(w)
        card.add_widget(self._custom_key)

        row = QHBoxLayout()
        for text, fn in (("Save & use", self._custom_save), ("Test", self._custom_test),
                         ("Remove", self._custom_remove)):
            b = FlatButton(text)
            b.clicked.connect(lambda _c=False, f=fn: f())
            row.addWidget(b)
        row.addStretch()
        self._custom_status = QLabel("")
        self._custom_status.setFont(dt.FONT_CAPTION)
        row.addWidget(self._custom_status)
        card.add_layout(row)
        self.body_layout.addWidget(card)

    def _custom_say(self, text: str, color):
        self._custom_status.setText(text)
        self._custom_status.setStyleSheet(f"color: {color.name()};")

    def _custom_save(self):
        url, model = self._custom_url.text().strip(), self._custom_model.text().strip()
        if not (url.startswith(("http://", "https://")) and model):
            self._custom_say("Need a http(s) URL and a model id", dt.WARNING)
            return
        if not self._cfg:
            return
        self._cfg.save_env_values({"GLANCE_CUSTOM_BASE_URL": url, "GLANCE_CUSTOM_MODEL": model,
                                   "GLANCE_CUSTOM_API_KEY": self._custom_key.get_key()})
        self._cfg.set_active_llm("custom")
        self._custom_say("✓ Saved — Custom is now the active provider", dt.SUCCESS)

    def _custom_test(self):
        url = self._custom_url.text().strip()
        if not url:
            self._custom_say("Enter a base URL first", dt.WARNING)
            return
        self._custom_say("Testing…", dt.TEXT_MUTED)
        t = _CustomTester(url, self._custom_key.get_key())
        t.finished.connect(lambda ok, msg: self._custom_say(msg, dt.SUCCESS if ok else dt.ERROR))
        self._validators.append(t)
        threading.Thread(target=t.run, daemon=True).start()

    def _custom_remove(self):
        if not self._cfg:
            return
        self._cfg.remove_env_values(["GLANCE_CUSTOM_BASE_URL", "GLANCE_CUSTOM_MODEL",
                                     "GLANCE_CUSTOM_API_KEY"])
        if self._cfg.llm_provider() == "custom" or \
                __import__("os").environ.get("GLANCE_ACTIVE_LLM") == "custom":
            self._cfg.set_active_llm("cloud")
        self._custom_url.clear()
        self._custom_model.clear()
        self._custom_key.clear_key()
        self._custom_say("Removed", dt.TEXT_MUTED)

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
