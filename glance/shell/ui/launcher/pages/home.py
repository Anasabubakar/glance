"""
Home — is Glance ready, what can it do right now, what just happened.

Layout: hero (status + the one primary action) → four capability tiles →
attention banners (only when something needs the user) → recent activity.
"""

from __future__ import annotations

import os
import re
import sys
import threading

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Banner, Card, Divider, FlatButton, GhostButton, GradientButton, PillBadge, StatCard

_LOG_RE = re.compile(r"^\[(\d\d:\d\d:\d\d)\.\d+\s*\+\s*[\d.]+s\]\s+(\w+)\s+(.*)$")
_NAMES = {"faster_whisper": "Faster-Whisper", "whisper_cpp": "Whisper.cpp", "deepgram": "Deepgram",
          "openai": "OpenAI", "edge_tts": "Edge voice", "elevenlabs": "ElevenLabs",
          "duckduckgo": "DuckDuckGo", "tavily": "Tavily"}
_CAT_VARIANT = {"HEAR": "info", "ROUTE": "accent", "ACT": "success", "TURN": "default",
                "TTS": "default", "WAKE": "warning"}


def _recent_events(limit: int = 7) -> list:
    """Meaningful, newest-first events from the session log (noise filtered)."""
    from pathlib import Path
    path = Path.home() / ".glance" / "logs" / "session.log"
    if not path.exists():
        return []
    out = []
    for line in reversed(path.read_text(errors="replace").splitlines()[-400:]):
        m = _LOG_RE.match(line)
        if not m:
            continue
        t, cat, msg = m.groups()
        if cat == "TURN" or (cat == "WAKE" and "MATCH" not in msg) or msg.strip() in ("''", '""', ""):
            continue
        out.append((t, cat, msg.strip()))
        if len(out) >= limit:
            break
    return out


class _HomeWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data: dict = {}
        try:
            from config import cfg
            data["llm"] = cfg.llm_provider()
            data["stt"] = cfg.stt_provider()
            data["tts"] = cfg.tts_provider()
            data["search"] = cfg.search_provider()
            data["hotkey"] = cfg.hotkey
            data["has_vision_key"] = bool(cfg.anthropic_api_key or cfg.openai_api_key or cfg.google_api_key)
        except Exception:
            pass
        try:
            from ai.ollama_bootstrap import is_ollama_running
            data["ollama_running"] = is_ollama_running()
        except Exception:
            data["ollama_running"] = False
        try:
            data["gnome"] = ("gnome" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
                             and sys.platform.startswith("linux"))
            if data["gnome"]:
                from screen import gnome_bridge
                data["ext_active"] = gnome_bridge.available() and not gnome_bridge.outdated()
        except Exception:
            pass
        try:
            data["events"] = _recent_events()
        except Exception:
            data["events"] = []
        self.result.emit(data)


class HomePage(BasePage):
    title = "Home"
    icon = "home"
    subtitle = "Start Glance and see what it can do right now."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._companion_running = False
        self._hotkey = "ctrl+alt+m"

        # ── Hero ────────────────────────────────────────────────────────────
        hero = Card(padding=28)
        hl = QHBoxLayout()
        hl.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(8)
        self._status_pill = PillBadge("Ready", "default")
        left.addWidget(self._status_pill, 0, Qt.AlignmentFlag.AlignLeft)
        self._headline = QLabel("Ready when you are")
        self._headline.setFont(dt.font(24, dt.QFont.Weight.DemiBold))
        left.addWidget(self._headline)
        self._tagline = QLabel("")
        self._tagline.setFont(dt.font(14))
        self._tagline.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._tagline.setWordWrap(True)
        left.addWidget(self._tagline)
        hl.addLayout(left, 1)
        self._launch_btn = GradientButton("Start Glance", icon="play")
        self._launch_btn.setFixedSize(176, 48)
        self._launch_btn.clicked.connect(self._on_launch)
        hl.addWidget(self._launch_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        hero.add_layout(hl)
        self.body_layout.addWidget(hero)

        # ── Getting started (first run only) ────────────────────────────────
        self._welcome = Card(padding=22)
        wl = QVBoxLayout()
        wl.setSpacing(14)
        head = QHBoxLayout()
        wt = QLabel("Getting started")
        wt.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        head.addWidget(wt)
        head.addStretch()
        hide = GhostButton("Hide")
        hide.clicked.connect(self._dismiss_welcome)
        head.addWidget(hide)
        wl.addLayout(head)
        self._steps = []
        for text, action in (("Choose your AI", ("AI & Keys", "api_keys")),
                             ("Start Glance", None),
                             ("Say “Glance, what can you do?”", None)):
            row = QHBoxLayout()
            row.setSpacing(12)
            mark = QLabel()
            mark.setFixedSize(22, 22)
            row.addWidget(mark)
            lbl = QLabel(text)
            lbl.setFont(dt.font(14))
            row.addWidget(lbl, 1)
            if action:
                b = FlatButton(action[0])
                b.clicked.connect(lambda _c=False, k=action[1]: self._goto(k))
                row.addWidget(b)
            wl.addLayout(row)
            self._steps.append((mark, lbl))
        self._welcome.add_layout(wl)
        self.body_layout.addWidget(self._welcome)
        self._welcome.setVisible(os.environ.get("GLANCE_ONBOARDED", "") != "1")

        # ── Capability tiles ────────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(12)
        self._tiles = {}
        for i, (key, label, ic) in enumerate([("llm", "AI model", "ai"), ("stt", "Hearing", "mic"),
                                              ("tts", "Voice", "volume"), ("search", "Web search", "search")]):
            tile = StatCard(label, "—", icon=ic)
            self._tiles[key] = tile
            grid.addWidget(tile, 0, i)
            grid.setColumnStretch(i, 1)
        self.body_layout.addLayout(grid)

        # ── Attention banners (filled in by on_activate) ────────────────────
        self._banners = QVBoxLayout()
        self._banners.setSpacing(10)
        self.body_layout.addLayout(self._banners)

        # ── Recent activity ─────────────────────────────────────────────────
        head = QHBoxLayout()
        head.addWidget(self.section_label("Recent activity"))
        head.addStretch()
        more = GhostButton("View all", icon=None)
        more.clicked.connect(lambda: self._goto("logs"))
        head.addWidget(more)
        self.body_layout.addLayout(head)
        self._activity = Card(padding=8)
        self._activity._layout.setSpacing(0)
        self.body_layout.addWidget(self._activity)
        self._set_activity([])
        self.body_layout.addStretch()
        self.set_companion_running(False)

    # ── data ────────────────────────────────────────────────────────────────
    def on_activate(self):
        w = _HomeWorker()
        w.result.connect(self._apply_data)
        self._worker = w
        threading.Thread(target=w.run, daemon=True).start()

    def _goto(self, key: str):
        win = self.window()
        if hasattr(win, "_navigate"):
            win._navigate(key)

    def _apply_data(self, data: dict):
        self._hotkey = data.get("hotkey", self._hotkey)
        self._refresh_tagline()
        self._refresh_steps(bool(data.get("llm")))
        labels = {"cloud": "Glance Cloud", "custom": "Custom endpoint", "claude": "Claude",
                  "openai": "OpenAI", "gemini": "Gemini", "copilot": "Copilot", "ollama": "Ollama"}
        for key, tile in self._tiles.items():
            raw = data.get(key) or ""
            if key == "llm":
                text = labels.get(raw, str(raw).title()) if raw else "Not set"
            else:
                text = _NAMES.get(raw, str(raw).replace("_", " ").title()) if raw else "Not set"
            tile.set_value(text, dt.TEXT_PRIMARY if raw else dt.TEXT_DIM)

        while self._banners.count():
            item = self._banners.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        llm = data.get("llm")
        if llm == "cloud":
            btn = FlatButton("Add a key")
            btn.clicked.connect(lambda: self._goto("api_keys"))
            self._banners.addWidget(Banner(
                "You're on the free Glance Cloud tier. It can chat and open apps, but it can't "
                "see your screen. Add a Gemini, Claude or OpenAI key so Glance can see and click.",
                "info", btn))
        if data.get("gnome") and not data.get("ext_active"):
            self._banners.addWidget(Banner(
                "Log out and back in once to switch on the always-on-top cursor, screen capture "
                "and the global hotkey on GNOME.", "warning"))
        if llm == "ollama" and not data.get("ollama_running"):
            btn = FlatButton("Open Local models")
            btn.clicked.connect(lambda: self._goto("ollama"))
            self._banners.addWidget(Banner("Ollama is selected but isn't running.", "warning", btn))
        self._set_activity(data.get("events", []))

    def _set_activity(self, events: list):
        self._activity.clear_layout()
        if not events:
            empty = QLabel("Nothing yet. Start Glance and say hello.")
            empty.setFont(dt.font(13))
            empty.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; padding: 18px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._activity.add_widget(empty)
            return
        for i, (t, cat, msg) in enumerate(events):
            if i:
                self._activity.add_widget(Divider())
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 11, 12, 11)
            rl.setSpacing(12)
            ts = QLabel(t)
            ts.setFont(dt.FONT_MONO)
            ts.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
            ts.setFixedWidth(64)
            rl.addWidget(ts)
            pill = PillBadge(cat.title(), _CAT_VARIANT.get(cat, "default"))
            pill.setMinimumWidth(64)
            rl.addWidget(pill)
            m = QLabel(msg if len(msg) < 96 else msg[:93] + "…")
            m.setFont(dt.font(13))
            m.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            rl.addWidget(m, 1)
            self._activity.add_widget(row)

    # ── launch / state ──────────────────────────────────────────────────────
    def _refresh_tagline(self):
        hk = self._hotkey.replace("+", " + ").upper().replace("CTRL", "Ctrl").replace("ALT", "Alt")
        if self._companion_running:
            self._tagline.setText(f"Say “Glance” or hold {hk} and speak.")
        else:
            self._tagline.setText(f"Start Glance, then say “Glance” or hold {hk}.")

    def _dismiss_welcome(self):
        os.environ["GLANCE_ONBOARDED"] = "1"
        try:
            from config import cfg
            cfg._persist_env("GLANCE_ONBOARDED", "1")
        except Exception:
            pass
        self._welcome.setVisible(False)

    def _refresh_steps(self, provider_ok: bool = True):
        from .. import icons
        states = [provider_ok, self._companion_running, False]
        for (mark, lbl), done in zip(self._steps, states):
            mark.setPixmap(icons.pixmap("check-circle" if done else "info",
                                        dt.SUCCESS.name() if done else dt.TEXT_DIM.name(), 20))
            lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name() if done else dt.TEXT_PRIMARY.name()};")

    def _on_launch(self):
        win = self.window()
        if hasattr(win, "start_companion"):
            win.start_companion()

    def set_companion_running(self, running: bool):
        self._companion_running = running
        if running:
            self._headline.setText("Glance is running")
            self._status_pill.set_state("Running", "success")
            self._launch_btn.setText("Running")
            self._launch_btn.setEnabled(False)
            if os.environ.get("GLANCE_ONBOARDED", "") != "1":
                self._dismiss_welcome()          # they've started Glance: onboarding is done
        else:
            self._headline.setText("Ready when you are")
            self._status_pill.set_state("Ready", "default")
            self._launch_btn.setText("Start Glance")
            self._launch_btn.setEnabled(True)
        self._refresh_tagline()
