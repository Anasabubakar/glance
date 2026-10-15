"""
AI & Keys — one place to choose which AI answers and to add its key.

A card per provider (Gemini, Claude, OpenAI, Copilot, Ollama,
Custom endpoint), each showing whether it is active / ready / needs a key, with
its key field right inside the card. Voice & search service keys sit below.
"""

from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget,
)

from .. import design_tokens as dt
from .. import icons
from ..page_base import BasePage
from ..widgets import (
    Card, Divider, FlatButton, GhostButton, GradientButton, IconTile, KeyField, PillBadge,
)


# ── key validation (runs off the UI thread) ─────────────────────────────────

class _Validator(QObject):
    finished = pyqtSignal(str, bool, str)

    def __init__(self, env_key: str, value: str):
        super().__init__()
        self.env_key, self.value = env_key, value

    def run(self):
        ok, msg = False, "Unknown provider"
        try:
            import httpx
            k, v = self.env_key, self.value
            r = None
            if k == "ANTHROPIC_API_KEY":
                r = httpx.get("https://api.anthropic.com/v1/models",
                              headers={"x-api-key": v, "anthropic-version": "2023-06-01"}, timeout=15)
                ok = r.status_code == 200
            elif k == "OPENAI_API_KEY":
                r = httpx.get("https://api.openai.com/v1/models",
                              headers={"Authorization": f"Bearer {v}"}, timeout=15)
                ok = r.status_code == 200
            elif k == "GOOGLE_API_KEY":
                # List models: validates the key without naming a model that Google
                # may have retired. Key goes in a header, never a URL.
                r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
                              headers={"x-goog-api-key": v}, timeout=15)
                ok = r.status_code in (200, 429)
            elif k == "DEEPGRAM_API_KEY":
                r = httpx.get("https://api.deepgram.com/v1/projects",
                              headers={"Authorization": f"Token {v}"}, timeout=15)
                ok = r.status_code == 200
            elif k == "ELEVENLABS_API_KEY":
                r = httpx.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": v}, timeout=15)
                ok = r.status_code == 200
            elif k == "TAVILY_API_KEY":
                r = httpx.post("https://api.tavily.com/search",
                               json={"api_key": v, "query": "test", "max_results": 1}, timeout=15)
                ok = r.status_code == 200
            if r is not None:
                msg = "Key works" if ok else f"Rejected (HTTP {r.status_code})"
        except Exception as e:                      # never echo URLs (they can hold keys)
            msg = "Couldn't reach the service" if "onnect" in type(e).__name__ else type(e).__name__
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
            self.finished.emit(ok, "Reachable" if ok else f"Rejected (HTTP {r.status_code})")
        except Exception as e:
            self.finished.emit(False, "Couldn't reach the server" if "onnect" in type(e).__name__
                               else type(e).__name__)


class _OllamaProbe(QObject):
    done = pyqtSignal(bool)

    def run(self):
        try:
            from ai.ollama_bootstrap import is_ollama_running
            self.done.emit(bool(is_ollama_running()))
        except Exception:
            self.done.emit(False)


# ── provider definitions ────────────────────────────────────────────────────

PROVIDERS = [
    # key, name, description, icon, env key (or None), help url
    ("gemini", "Google Gemini", "Sees your screen and clicks. Has a free tier.",
     "ai", "GOOGLE_API_KEY", "https://aistudio.google.com/apikey"),
    ("claude", "Claude", "Best at screen tasks and computer use.",
     "ai", "ANTHROPIC_API_KEY", "https://console.anthropic.com/settings/keys"),
    ("openai", "OpenAI", "GPT models with vision.",
     "ai", "OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
    ("copilot", "GitHub Copilot", "Use your existing Copilot subscription.",
     "link", None, None),
    ("ollama", "Ollama (on this computer)", "Private and offline. Needs a model downloaded.",
     "cpu", None, None),
    ("custom", "Custom endpoint", "Any OpenAI-compatible server: OpenRouter, Groq, LM Studio, your own.",
     "link", None, None),
]

SERVICES = [
    ("DEEPGRAM_API_KEY", "Deepgram", "Faster, more accurate speech-to-text", "deepgram_api_key",
     "https://console.deepgram.com"),
    ("ELEVENLABS_API_KEY", "ElevenLabs", "Natural voice for Glance's replies", "elevenlabs_api_key",
     "https://elevenlabs.io/app/settings/api-keys"),
    ("TAVILY_API_KEY", "Tavily", "Better web search results", "tavily_api_key", "https://app.tavily.com"),
]

_CFG_ATTR = {"GOOGLE_API_KEY": "google_api_key", "ANTHROPIC_API_KEY": "anthropic_api_key",
             "OPENAI_API_KEY": "openai_api_key"}


def _open(url: str):
    QDesktopServices.openUrl(QUrl(url))


class _Status(QLabel):
    """One-line result text under a card's buttons."""

    def __init__(self):
        super().__init__("")
        self.setFont(dt.font(13))
        self.setWordWrap(True)

    def say(self, text: str, color):
        self.setText(text)
        self.setStyleSheet(f"color: {color.name()};")


def _hint(text: str) -> QLabel:
    h = QLabel(text)
    h.setWordWrap(True)
    h.setFont(dt.font(13))
    h.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
    return h


class ProviderCard(Card):
    """Header (identity, status, action) + an expandable body for credentials."""

    activate_requested = pyqtSignal(str)

    def __init__(self, page: "APIKeysPage", spec: tuple):
        super().__init__(padding=18)
        self.page = page
        self.pkey, self.name, self.desc, self.icon_name, self.env_key, self.help_url = spec
        self._validators: list = []
        self._layout.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(14)
        head.addWidget(IconTile(self.icon_name, 42), 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        t = QLabel(self.name)
        t.setFont(dt.font(15, dt.QFont.Weight.DemiBold))
        title_row.addWidget(t)
        self.pill = PillBadge("", "default")
        title_row.addWidget(self.pill)
        title_row.addStretch()
        text.addLayout(title_row)
        text.addWidget(_hint(self.desc))
        head.addLayout(text, 1)
        self.action = FlatButton("Use this")
        self.action.setMinimumWidth(104)
        self._needs_setup = False
        self.action.clicked.connect(self._on_action)
        head.addWidget(self.action, 0, Qt.AlignmentFlag.AlignVCenter)
        self.chev = GhostButton("")
        self.chev.setFixedSize(34, 34)
        self.chev.setIcon(icons.icon("chevron-right", dt.TEXT_MUTED.name(), 18))
        self.chev.clicked.connect(self._toggle)
        self.chev.setVisible(self.env_key is not None or self.pkey in ("custom", "ollama"))
        head.addWidget(self.chev, 0, Qt.AlignmentFlag.AlignVCenter)
        self._layout.addLayout(head)

        self.body = QWidget()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)
        bl.addWidget(Divider())
        self.status = _Status()
        self._build_body(bl)
        bl.addWidget(self.status)
        self._layout.addWidget(self.body)
        self.body.setVisible(False)

    def _buttons(self, bl, primary_text, on_primary, on_test, on_remove, link=None):
        row = QHBoxLayout()
        row.setSpacing(8)
        save = GradientButton(primary_text)
        save.setMinimumHeight(38)
        save.clicked.connect(on_primary)
        test = FlatButton("Test")
        test.clicked.connect(on_test)
        rm = GhostButton("Remove")
        rm.clicked.connect(on_remove)
        for b in (save, test, rm):
            row.addWidget(b)
        row.addStretch()
        if link:
            lk = GhostButton("Get a key", icon="external")
            lk.clicked.connect(lambda: _open(link))
            row.addWidget(lk)
        bl.addLayout(row)

    def _build_body(self, bl: QVBoxLayout):
        cfg = self.page.cfg
        if self.pkey == "custom":
            bl.addWidget(_hint("Point Glance at any server that speaks the OpenAI API. Choose a "
                               "vision-capable model to keep screen features."))
            self.url = QLineEdit(getattr(cfg, "custom_base_url", "") if cfg else "")
            self.url.setPlaceholderText("Base URL — https://openrouter.ai/api/v1")
            self.model = QLineEdit(getattr(cfg, "custom_model", "") if cfg else "")
            self.model.setPlaceholderText("Model — anthropic/claude-sonnet-4.5")
            bl.addWidget(self.url)
            bl.addWidget(self.model)
            self.key = KeyField("API key (optional for local servers)", "GLANCE_CUSTOM_API_KEY",
                                getattr(cfg, "custom_api_key", "") if cfg else "")
            bl.addWidget(self.key)
            self._buttons(bl, "Save & use", self._custom_save, self._custom_test, self._custom_remove)
        elif self.env_key:
            cur = getattr(cfg, _CFG_ATTR[self.env_key], "") if cfg else ""
            self.key = KeyField("API key", self.env_key, cur or "")
            bl.addWidget(self.key)
            self._buttons(bl, "Save", self._save, self._test, self._remove, self.help_url)
        elif self.pkey == "ollama":
            bl.addWidget(_hint("Ollama runs models on your own computer. Manage and download them under "
                               "Local models."))
            go = FlatButton("Open Local models", icon="cpu")
            go.clicked.connect(lambda: self.page.goto("ollama"))
            row = QHBoxLayout()
            row.addWidget(go)
            row.addStretch()
            bl.addLayout(row)

    def _on_action(self):
        if self._needs_setup:
            if not self.body.isVisible():
                self._toggle()           # open the key field instead of activating
            return
        self.activate_requested.emit(self.pkey)

    def _toggle(self):
        show = not self.body.isVisible()
        self.body.setVisible(show)
        self.chev.setIcon(icons.icon("chevron-down" if show else "chevron-right", dt.TEXT_MUTED.name(), 18))

    # key actions ---------------------------------------------------------------
    def _save(self):
        v = self.key.get_key()
        if not v:
            self.status.say("Paste a key first.", dt.WARNING)
            return
        self.page.cfg.save_env_values({self.env_key: v})
        self.status.say("Saved. Use Test to check that it works.", dt.SUCCESS)
        self.page.refresh()

    def _test(self):
        v = self.key.get_key()
        if not v:
            self.status.say("Paste a key first.", dt.WARNING)
            return
        self.status.say("Testing…", dt.TEXT_MUTED)
        val = _Validator(self.env_key, v)
        val.finished.connect(self._on_tested)
        self._validators.append(val)
        threading.Thread(target=val.run, daemon=True).start()

    def _on_tested(self, _k: str, ok: bool, msg: str):
        self.key.set_status(ok)
        self.status.say(msg, dt.SUCCESS if ok else dt.ERROR)

    def _remove(self):
        if QMessageBox.question(self, "Remove key", f"Remove your {self.name} key from this computer?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) \
                != QMessageBox.StandardButton.Yes:
            return
        self.page.cfg.remove_env_values([self.env_key])
        self.page.cfg.save_env_values({})              # refresh live config fields
        self.key.clear_key()
        self.status.say("Removed.", dt.TEXT_MUTED)
        self.page.refresh()

    def _custom_save(self):
        url, model = self.url.text().strip(), self.model.text().strip()
        if not (url.startswith(("http://", "https://")) and model):
            self.status.say("Enter a URL starting with http(s):// and a model name.", dt.WARNING)
            return
        self.page.cfg.save_env_values({"GLANCE_CUSTOM_BASE_URL": url, "GLANCE_CUSTOM_MODEL": model,
                                       "GLANCE_CUSTOM_API_KEY": self.key.get_key()})
        self.page.cfg.set_active_llm("custom")
        self.status.say("Saved. Custom endpoint is now in use.", dt.SUCCESS)
        self.page.refresh()

    def _custom_test(self):
        url = self.url.text().strip()
        if not url:
            self.status.say("Enter a base URL first.", dt.WARNING)
            return
        self.status.say("Testing…", dt.TEXT_MUTED)
        t = _CustomTester(url, self.key.get_key())
        t.finished.connect(lambda ok, msg: self.status.say(msg, dt.SUCCESS if ok else dt.ERROR))
        self._validators.append(t)
        threading.Thread(target=t.run, daemon=True).start()

    def _custom_remove(self):
        self.page.cfg.remove_env_values(["GLANCE_CUSTOM_BASE_URL", "GLANCE_CUSTOM_MODEL",
                                         "GLANCE_CUSTOM_API_KEY"])
        if self.page.cfg.llm_provider() == "custom":
            self.page.cfg.remove_env_values(["GLANCE_ACTIVE_LLM"])
        self.url.clear()
        self.model.clear()
        self.key.clear_key()
        self.status.say("Removed.", dt.TEXT_MUTED)
        self.page.refresh()

    # state ---------------------------------------------------------------------
    def set_state(self, active: bool, ready: bool, note: str = "", selectable: bool | None = None):
        border = dt.ACCENT_LINE if active else dt.BORDER_CSS
        self.setStyleSheet(f"QFrame#Card {{ background: {dt.BG_CARD.name()}; border: 1px solid {border}; "
                           f"border-radius: {dt.CARD_RADIUS}px; }}")
        has_body = self.env_key is not None or self.pkey == "custom"
        self._needs_setup = (not ready) and has_body and not active
        if active:
            self.pill.set_state("In use", "accent")
            self.action.setText("In use")
            self.action.setEnabled(False)
            return
        self.pill.set_state(note or ("Ready" if ready else "Needs setup"), "success" if ready else "warning")
        if self._needs_setup:
            self.action.setText("Add key" if self.env_key else "Set up")
            self.action.setEnabled(True)
        else:
            self.action.setText("Use this")
            self.action.setEnabled(ready if selectable is None else selectable)


class APIKeysPage(BasePage):
    title = "AI & Keys"
    icon = "key"
    subtitle = "Choose which AI answers, and add its key. Keys stay on this computer."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from config import cfg
            self.cfg = cfg
        except Exception:
            self.cfg = None
        self._cards: dict[str, ProviderCard] = {}
        self._svc_fields: dict[str, KeyField] = {}
        self._svc_status: dict[str, _Status] = {}
        self._validators: list = []
        self._ollama_ok = False

        self.body_layout.addWidget(self.section_label("Your AI"))
        for spec in PROVIDERS:
            card = ProviderCard(self, spec)
            card.activate_requested.connect(self._activate)
            self._cards[spec[0]] = card
            self.body_layout.addWidget(card)

        self.body_layout.addWidget(self.section_label("Voice & search"))
        self.body_layout.addWidget(self.hint_label(
            "Optional services that help Glance hear better, sound better and search better."))
        svc = Card(padding=20)
        svc._layout.setSpacing(16)
        for i, (env, name, desc, attr, url) in enumerate(SERVICES):
            if i:
                svc.add_widget(Divider())
            cur = getattr(self.cfg, attr, "") if self.cfg else ""
            head = QHBoxLayout()
            col = QVBoxLayout()
            col.setSpacing(2)
            n = QLabel(name)
            n.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
            col.addWidget(n)
            col.addWidget(_hint(desc))
            head.addLayout(col, 1)
            link = GhostButton("Get a key", icon="external")
            link.clicked.connect(lambda _c=False, u=url: _open(u))
            head.addWidget(link)
            svc.add_layout(head)
            field = KeyField("", env, cur or "")
            self._svc_fields[env] = field
            svc.add_widget(field)
            row = QHBoxLayout()
            row.setSpacing(8)
            save = GradientButton("Save")
            save.setMinimumHeight(36)
            save.clicked.connect(lambda _c=False, e=env: self._svc_save(e))
            test = FlatButton("Test")
            test.clicked.connect(lambda _c=False, e=env: self._svc_test(e))
            rm = GhostButton("Remove")
            rm.clicked.connect(lambda _c=False, e=env: self._svc_remove(e))
            for b in (save, test, rm):
                row.addWidget(b)
            row.addStretch()
            st = _Status()
            self._svc_status[env] = st
            row.addWidget(st)
            svc.add_layout(row)
        self.body_layout.addWidget(svc)
        self.body_layout.addStretch()
        self.refresh()

    # ── navigation / state ─────────────────────────────────────────────────
    def goto(self, key: str):
        win = self.window()
        if hasattr(win, "_navigate"):
            win._navigate(key)

    def on_activate(self):
        p = _OllamaProbe()
        p.done.connect(self._on_ollama)
        self._probe = p
        threading.Thread(target=p.run, daemon=True).start()
        self.refresh()

    def _on_ollama(self, ok: bool):
        self._ollama_ok = ok
        self.refresh()

    def refresh(self):
        c = self.cfg
        if not c:
            return
        active = c.llm_provider()
        copilot = "copilot" in c.available_llm_providers()
        state = {  # key: (ready, note, selectable)
            "cloud":   (True, "Free", None),
            "gemini":  (bool(c.google_api_key), "Key saved" if c.google_api_key else "Needs a key", None),
            "claude":  (bool(c.anthropic_api_key), "Key saved" if c.anthropic_api_key else "Needs a key", None),
            "openai":  (bool(c.openai_api_key), "Key saved" if c.openai_api_key else "Needs a key", None),
            "copilot": (copilot, "Signed in" if copilot else "Sign in from the tray", None),
            "ollama":  (self._ollama_ok, "Running" if self._ollama_ok else "Not running", True),
            "custom":  (c.custom_ready(), "Configured" if c.custom_ready() else "Needs setup", None),
        }
        for key, card in self._cards.items():
            ready, note, selectable = state[key]
            card.set_state(key == active, ready, note, selectable)

    def _activate(self, key: str):
        if self.cfg:
            self.cfg.set_active_llm(key)
        self.refresh()

    # ── voice & search services ───────────────────────────────────────────
    def _svc_save(self, env: str):
        v = self._svc_fields[env].get_key()
        if not v:
            self._svc_status[env].say("Paste a key first.", dt.WARNING)
            return
        self.cfg.save_env_values({env: v})
        self._svc_status[env].say("Saved", dt.SUCCESS)

    def _svc_test(self, env: str):
        v = self._svc_fields[env].get_key()
        if not v:
            self._svc_status[env].say("Paste a key first.", dt.WARNING)
            return
        self._svc_status[env].say("Testing…", dt.TEXT_MUTED)
        val = _Validator(env, v)
        val.finished.connect(lambda e, ok, msg: (self._svc_fields[e].set_status(ok),
                                                 self._svc_status[e].say(msg, dt.SUCCESS if ok else dt.ERROR)))
        self._validators.append(val)
        threading.Thread(target=val.run, daemon=True).start()

    def _svc_remove(self, env: str):
        self.cfg.remove_env_values([env])
        self.cfg.save_env_values({})
        self._svc_fields[env].clear_key()
        self._svc_status[env].say("Removed", dt.TEXT_MUTED)
