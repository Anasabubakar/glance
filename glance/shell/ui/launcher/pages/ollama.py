"""Ollama page — install/status, model pull with progress, selection."""

import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QObject, Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton, GradientButton, StatusDot
from .. import design_tokens as dt


class _StatusWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        try:
            from ai.ollama_bootstrap import is_ollama_running, is_ollama_installed, list_installed_models
            data["installed"] = is_ollama_installed()
            data["running"] = is_ollama_running()
            data["models"] = list_installed_models() if data["running"] else []
        except Exception as e:
            data["installed"] = False
            data["running"] = False
            data["models"] = []
        try:
            from config import cfg
            data["vision_model"] = cfg.ollama_vision_model or ""
            data["text_model"] = cfg.ollama_text_model or ""
            data["host"] = cfg.ollama_host or "http://localhost:11434"
        except Exception:
            data["vision_model"] = ""
            data["text_model"] = ""
            data["host"] = "http://localhost:11434"
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

            def on_progress(pct):
                self.progress.emit(self.model_name, pct)

            pull_model(self.model_name, on_progress)
            self.finished.emit(self.model_name, True, "")
        except Exception as e:
            self.finished.emit(self.model_name, False, str(e)[:120])


class OllamaPage(BasePage):
    title = "Ollama"
    icon = "\U0001F999"
    subtitle = "Manage your local Ollama installation and models."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []

        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # Status section
        self.body_layout.addWidget(self.section_label("Status"))
        status_card = Card()
        status_row = QHBoxLayout()
        self._status_dot = StatusDot(dt.TEXT_DIM)
        status_row.addWidget(self._status_dot)
        self._status_label = QLabel("Checking…")
        self._status_label.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
        self._status_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        self._host_label = QLabel("")
        self._host_label.setFont(dt.FONT_CAPTION)
        self._host_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        status_row.addWidget(self._host_label)
        status_card.add_layout(status_row)
        self.body_layout.addWidget(status_card)

        # Model selection
        self.body_layout.addWidget(self.section_label("Active Models"))

        select_card = Card()
        for kind, label in [("vision", "Vision Model"), ("text", "Text Model")]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFont(dt.FONT_BODY)
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            row.addWidget(lbl)
            combo = QComboBox()
            combo.setMinimumWidth(220)
            combo.setStyleSheet(f"""
                QComboBox {{
                    background: {dt.BG_ELEVATED.name()};
                    color: {dt.TEXT_PRIMARY.name()};
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 6px;
                    padding: 6px 10px;
                }}
                QComboBox::drop-down {{ border: none; }}
                QComboBox QAbstractItemView {{
                    background: {dt.BG_CARD.name()};
                    color: {dt.TEXT_PRIMARY.name()};
                    selection-background-color: rgba(100,107,242,0.2);
                }}
            """)
            combo.currentTextChanged.connect(
                lambda text, k=kind: self._set_model(k, text)
            )
            row.addWidget(combo, 1)
            setattr(self, f"_{kind}_combo", combo)
            select_card.add_layout(row)
        self.body_layout.addWidget(select_card)

        # Installed models
        self.body_layout.addWidget(self.section_label("Installed Models"))
        self._models_container = QVBoxLayout()
        self._models_container.setSpacing(4)
        self._no_models_label = QLabel("Checking…")
        self._no_models_label.setFont(dt.FONT_CAPTION)
        self._no_models_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._models_container.addWidget(self._no_models_label)
        self.body_layout.addLayout(self._models_container)

        # Pull section
        self.body_layout.addWidget(self.section_label("Pull New Model"))
        pull_card = Card()
        pull_row = QHBoxLayout()
        self._pull_combo = QComboBox()
        self._pull_combo.setMinimumWidth(260)
        self._pull_combo.setEditable(True)
        self._pull_combo.setStyleSheet(f"""
            QComboBox {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 6px 10px;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        try:
            from ai.ollama_models_registry import RECOMMENDED_VISION, RECOMMENDED_TEXT
            for m in RECOMMENDED_VISION + RECOMMENDED_TEXT:
                name = m if isinstance(m, str) else m.get("name", str(m))
                self._pull_combo.addItem(name)
        except Exception:
            self._pull_combo.addItem("llava")
            self._pull_combo.addItem("llama3.2")
        pull_row.addWidget(self._pull_combo, 1)

        self._pull_btn = GradientButton("Pull")
        self._pull_btn.setFixedWidth(80)
        self._pull_btn.setFixedHeight(36)
        self._pull_btn.clicked.connect(self._pull_model)
        pull_row.addWidget(self._pull_btn)
        pull_card.add_layout(pull_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {dt.BG_ELEVATED.name()};
                border: none;
                border-radius: 4px;
                height: 8px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()});
                border-radius: 4px;
            }}
        """)
        pull_card.add_widget(self._progress_bar)

        self._pull_status = QLabel("")
        self._pull_status.setFont(dt.FONT_CAPTION)
        self._pull_status.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        pull_card.add_widget(self._pull_status)

        self.body_layout.addWidget(pull_card)
        self.body_layout.addStretch()

    def on_activate(self):
        w = _StatusWorker()
        w.result.connect(self._apply_status)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply_status(self, data: dict):
        running = data.get("running", False)
        installed = data.get("installed", False)
        models = data.get("models", [])

        if running:
            self._status_dot.set_color(dt.SUCCESS)
            self._status_label.setText("Running")
        elif installed:
            self._status_dot.set_color(dt.WARNING)
            self._status_label.setText("Installed but not running")
        else:
            self._status_dot.set_color(dt.ERROR)
            self._status_label.setText("Not installed")

        self._host_label.setText(data.get("host", ""))

        # Clear models list
        while self._models_container.count():
            item = self._models_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if models:
            for m in models:
                name = m if isinstance(m, str) else getattr(m, "name", str(m))
                lbl = QLabel(f"  •  {name}")
                lbl.setFont(dt.FONT_BODY)
                lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
                self._models_container.addWidget(lbl)
        else:
            lbl = QLabel("No models installed." if running else "Start Ollama to see models.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._models_container.addWidget(lbl)

        # Update combos
        for kind in ("vision", "text"):
            combo = getattr(self, f"_{kind}_combo", None)
            if not combo:
                continue
            combo.blockSignals(True)
            combo.clear()
            for m in models:
                name = m if isinstance(m, str) else getattr(m, "name", str(m))
                combo.addItem(name)
            current = data.get(f"{kind}_model", "")
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def _set_model(self, kind: str, name: str):
        if self._cfg and name:
            self._cfg.set_ollama_model(kind, name)

    def _pull_model(self):
        name = self._pull_combo.currentText().strip()
        if not name:
            return
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._pull_btn.setEnabled(False)
        self._pull_status.setText(f"Pulling {name}…")
        self._pull_status.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")

        w = _PullWorker(name)
        w.progress.connect(self._on_pull_progress)
        w.finished.connect(self._on_pull_finished)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _on_pull_progress(self, name: str, pct: float):
        self._progress_bar.setValue(int(pct * 100))

    def _on_pull_finished(self, name: str, ok: bool, error: str):
        self._pull_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        if ok:
            self._pull_status.setText(f"Successfully pulled {name}")
            self._pull_status.setStyleSheet(f"color: {dt.SUCCESS.name()};")
            self.on_activate()
        else:
            self._pull_status.setText(f"Failed: {error}")
            self._pull_status.setStyleSheet(f"color: {dt.ERROR.name()};")
