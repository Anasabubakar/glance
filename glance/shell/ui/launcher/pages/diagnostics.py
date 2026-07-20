"""
Diagnostics page — system info, provider health, cache sizes.
"""

import threading
import sys
import platform

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QObject

from ..page_base import BasePage
from ..widgets import Card, GradientButton, FlatButton, LoadingSpinner
from .. import design_tokens as dt


class _DiagWorker(QObject):
    result = pyqtSignal(dict)

    def run(self):
        data = {}
        data["python"] = sys.version.split()[0]
        data["platform"] = platform.platform()
        data["os"] = f"{platform.system()} {platform.release()}"
        data["frozen"] = getattr(sys, "frozen", False)

        try:
            from config import cfg
            data["llm"] = cfg.llm_provider()
            data["stt"] = cfg.stt_provider()
            data["tts"] = cfg.tts_provider()
            data["search"] = cfg.search_provider()
            data["ollama_host"] = cfg.ollama_host or "http://localhost:11434"
        except Exception:
            pass

        try:
            from ai.ollama_bootstrap import is_ollama_running, list_installed_models
            data["ollama_running"] = is_ollama_running()
            data["ollama_models"] = list_installed_models() if data["ollama_running"] else []
        except Exception:
            data["ollama_running"] = False
            data["ollama_models"] = []

        try:
            import os
            if sys.platform == "win32":
                cache_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
            else:
                cache_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Glance"
            cache_files = list(cache_dir.glob("models_*.json"))
            data["cache_files"] = len(cache_files)
            data["cache_size"] = sum(f.stat().st_size for f in cache_files)
        except Exception:
            data["cache_files"] = 0
            data["cache_size"] = 0
        self.result.emit(data)


from pathlib import Path


class DiagnosticsPage(BasePage):
    title = "Diagnostics"
    icon = "🔍"
    subtitle = "System information and provider health checks."

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list = []

        self._report = QTextEdit()
        self._report.setReadOnly(True)
        self._report.setFont(dt.FONT_MONO)
        self._report.setStyleSheet(dt.TEXTEDIT_QSS)
        self._report.setMinimumHeight(350)
        self.body_layout.addWidget(self._report, 1)

        self._spinner = LoadingSpinner(20)
        self._spinner.hide()

        btn_row = QHBoxLayout()
        self._run_btn = GradientButton("Run Diagnostics")
        self._run_btn.setFixedHeight(40)
        self._run_btn.clicked.connect(self.on_activate)
        btn_row.addWidget(self._run_btn)
        btn_row.addWidget(self._spinner)

        save_btn = FlatButton("Save Report")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        self.body_layout.addLayout(btn_row)

    def on_activate(self):
        self._report.setPlainText("Running diagnostics…")
        self._run_btn.setEnabled(False)
        self._spinner.start()
        w = _DiagWorker()
        w.result.connect(self._apply)
        self._workers.append(w)
        threading.Thread(target=w.run, daemon=True).start()

    def _apply(self, data: dict):
        self._spinner.stop()
        self._run_btn.setEnabled(True)
        lines = [
            "=== Glance Diagnostics ===",
            "",
            f"Python:    {data.get('python', '?')}",
            f"Platform:  {data.get('platform', '?')}",
            f"OS:        {data.get('os', '?')}",
            f"Frozen:    {data.get('frozen', False)}",
            "",
            "--- Providers ---",
            f"LLM:       {data.get('llm', 'none')}",
            f"STT:       {data.get('stt', 'none')}",
            f"TTS:       {data.get('tts', 'none')}",
            f"Search:    {data.get('search', 'none')}",
            "",
            "--- Ollama ---",
            f"Host:      {data.get('ollama_host', '?')}",
            f"Running:   {data.get('ollama_running', False)}",
            f"Models:    {', '.join(data.get('ollama_models', [])) or 'none'}",
            "",
            "--- Cache ---",
            f"Files:     {data.get('cache_files', 0)}",
            f"Size:      {data.get('cache_size', 0) / 1024:.1f} KB",
        ]
        self._report.setPlainText("\n".join(lines))

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagnostics", "glance_diagnostics.txt", "Text Files (*.txt)"
        )
        if path:
            try:
                Path(path).write_text(self._report.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
