"""
On this computer — run AI models locally with Ollama (private, offline).

Status first (with a clear next step if Ollama isn't installed or running), then
which downloaded models Glance should use, then one-click downloads.
"""

from __future__ import annotations

import subprocess
import threading

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QVBoxLayout, QWidget

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import (
    Banner, Card, Divider, FlatButton, GradientButton, IconTile, PillBadge,
)

RECOMMENDED = [
    ("qwen2.5vl:3b", "Qwen 2.5 VL 3B", "Sees your screen. Small and quick.", "~3 GB", True),
    ("llama3.2-vision", "Llama 3.2 Vision", "Sees your screen. Larger, more capable.", "~8 GB", True),
    ("llama3.2:3b", "Llama 3.2 3B", "Fast text chat and quick answers.", "~2 GB", False),
    ("qwen3:8b", "Qwen 3 8B", "Stronger text reasoning.", "~5 GB", False),
]


class _StatusWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {"installed": False, "running": False, "models": []}
        try:
            from ai.ollama_bootstrap import is_ollama_installed, is_ollama_running, list_installed_models
            data["installed"] = is_ollama_installed()
            data["running"] = is_ollama_running()
            data["models"] = [str(m) for m in (list_installed_models() if data["running"] else [])]
        except Exception:
            pass
        try:
            from config import cfg
            data["vision_model"] = cfg.ollama_vision_model or ""
            data["text_model"] = cfg.ollama_text_model or ""
            data["host"] = cfg.ollama_host or "http://localhost:11434"
        except Exception:
            pass
        self.result.emit(data)


class _PullWorker(QObject):
    progress = pyqtSignal(str, float)
    finished = pyqtSignal(str, bool, str)

    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    def run(self):
        try:
            from ai.ollama_bootstrap import pull_model
            pull_model(self.model_name, lambda pct: self.progress.emit(self.model_name, pct))
            self.finished.emit(self.model_name, True, "")
        except Exception as e:
            self.finished.emit(self.model_name, False, str(e)[:140])


def _combo() -> QComboBox:
    c = QComboBox()
    c.setMinimumWidth(240)
    return c


class OllamaPage(BasePage):
    title = "On this computer"
    icon = "cpu"
    subtitle = "Run AI models locally with Ollama: private and offline."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []
        self._installed: list = []
        self._pulling: set = set()
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # ── Status ──────────────────────────────────────────────────────────
        self._status = Card(padding=20)
        self.body_layout.addWidget(self._status)
        self._status_banner = QVBoxLayout()
        self.body_layout.addLayout(self._status_banner)
        self._render_status("checking", "")

        # ── Which models Glance uses ────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Models Glance uses"))
        self.body_layout.addWidget(self.hint_label("The vision model reads your screen; the text model handles "
                                                   "everyday chat. Download models below."))
        sel = Card(padding=20)
        sel._layout.setSpacing(16)
        for kind, label, desc in (("vision", "Vision model", "Used when Glance needs to see your screen"),
                                  ("text", "Text model", "Used for quick answers and chat")):
            row = QHBoxLayout()
            col = QVBoxLayout()
            col.setSpacing(2)
            t = QLabel(label)
            t.setFont(dt.font(14, dt.QFont.Weight.Medium))
            col.addWidget(t)
            col.addWidget(self.hint_label(desc))
            row.addLayout(col, 1)
            combo = _combo()
            combo.currentTextChanged.connect(lambda text, k=kind: self._set_model(k, text))
            setattr(self, f"_{kind}_combo", combo)
            row.addWidget(combo)
            sel.add_layout(row)
            if kind == "vision":
                sel.add_widget(Divider())
        self.body_layout.addWidget(sel)

        # ── Downloads ───────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Download a model"))
        self._list = Card(padding=8)
        self._list._layout.setSpacing(0)
        self.body_layout.addWidget(self._list)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{ background: {dt.BG_INPUT.name()}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()}); }}""")
        self.body_layout.addWidget(self._progress)
        self._pull_status = QLabel("")
        self._pull_status.setFont(dt.font(13))
        self.body_layout.addWidget(self._pull_status)

        custom = Card(padding=20)
        t = QLabel("Any other model")
        t.setFont(dt.font(14, dt.QFont.Weight.Medium))
        custom.add_widget(t)
        row = QHBoxLayout()
        row.setSpacing(10)
        self._custom = QLineEdit()
        self._custom.setPlaceholderText("model name from ollama.com/library, e.g. mistral")
        row.addWidget(self._custom, 1)
        go = FlatButton("Download")
        go.clicked.connect(lambda: self._pull(self._custom.text().strip()))
        row.addWidget(go)
        custom.add_layout(row)
        self.body_layout.addWidget(custom)
        self.body_layout.addStretch()
        self._render_list()

    # ── status ──────────────────────────────────────────────────────────────
    def on_activate(self):
        w = _StatusWorker()
        w.result.connect(self._apply_status)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _render_status(self, state: str, host: str):
        self._status.clear_layout()
        while self._status_banner.count():
            it = self._status_banner.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        meta = {
            "checking": ("Checking Ollama…", "default", "Looking for Ollama on this computer."),
            "running": ("Ollama is running", "success", f"Ready to use local models at {host}."),
            "stopped": ("Ollama is installed but not running", "warning",
                        "Start it to use local models."),
            "missing": ("Ollama isn't installed", "warning",
                        "Ollama is the free app that runs AI models on your computer."),
        }
        title, variant, desc = meta[state]
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(IconTile("cpu", 44), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        tr = QHBoxLayout()
        t = QLabel(title)
        t.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        tr.addWidget(t)
        tr.addWidget(PillBadge({"running": "Running", "stopped": "Stopped", "missing": "Not installed",
                                "checking": "Checking"}[state], variant))
        tr.addStretch()
        col.addLayout(tr)
        col.addWidget(self.hint_label(desc))
        row.addLayout(col, 1)
        if state == "missing":
            b = GradientButton("Get Ollama", icon="external")
            b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://ollama.com/download")))
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        elif state == "stopped":
            b = GradientButton("Start Ollama", icon="play")
            b.clicked.connect(self._start_ollama)
            row.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        self._status.add_layout(row)

    def _start_ollama(self):
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except Exception:
            pass
        threading.Timer(2.5, self.on_activate).start()

    def _apply_status(self, data: dict):
        running, installed = data.get("running", False), data.get("installed", False)
        self._render_status("running" if running else "stopped" if installed else "missing",
                            data.get("host", ""))
        self._installed = data.get("models", [])
        for kind in ("vision", "text"):
            combo = getattr(self, f"_{kind}_combo")
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(self._installed or ["No models downloaded yet"])
            combo.setEnabled(bool(self._installed))
            idx = combo.findText(data.get(f"{kind}_model", ""))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
        self._render_list()

    def _set_model(self, kind: str, name: str):
        if self._cfg and name and name in self._installed:
            self._cfg.set_ollama_model(kind, name)

    # ── downloads ───────────────────────────────────────────────────────────
    def _have(self, name: str) -> bool:
        base = name.split(":")[0]
        return any(m == name or m.split(":")[0] == base and ":" not in name for m in self._installed)

    def _render_list(self):
        self._list.clear_layout()
        for i, (mid, label, desc, size, vision) in enumerate(RECOMMENDED):
            if i:
                self._list.add_widget(Divider())
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 12, 12, 12)
            rl.setSpacing(12)
            col = QVBoxLayout()
            col.setSpacing(2)
            tr = QHBoxLayout()
            n = QLabel(label)
            n.setFont(dt.font(14, dt.QFont.Weight.Medium))
            tr.addWidget(n)
            tr.addWidget(PillBadge("Vision" if vision else "Text", "info" if vision else "default"))
            tr.addStretch()
            col.addLayout(tr)
            col.addWidget(self.hint_label(f"{desc}  ·  {size}"))
            rl.addLayout(col, 1)
            if self._have(mid):
                rl.addWidget(PillBadge("Downloaded", "success"))
            elif mid in self._pulling:
                rl.addWidget(PillBadge("Downloading…", "accent"))
            else:
                b = FlatButton("Download", icon="download")
                b.clicked.connect(lambda _c=False, m=mid: self._pull(m))
                rl.addWidget(b)
            self._list.add_widget(row)

    def _pull(self, name: str):
        if not name or name in self._pulling:
            return
        self._pulling.add(name)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._pull_status.setText(f"Downloading {name}…")
        self._pull_status.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._render_list()
        w = _PullWorker(name)
        w.progress.connect(lambda _n, pct: self._progress.setValue(int(pct)))
        w.finished.connect(self._on_pulled)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _on_pulled(self, name: str, ok: bool, error: str):
        self._pulling.discard(name)
        self._progress.setVisible(False)
        self._pull_status.setText(f"{name} is ready." if ok else f"Couldn't download {name}: {error}")
        self._pull_status.setStyleSheet(f"color: {(dt.SUCCESS if ok else dt.ERROR).name()};")
        self.on_activate()
