"""
Logs page — session.log viewer with category filter, search, export.
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QComboBox, QLineEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton, DangerButton, SearchField
from .. import design_tokens as dt

_CATEGORIES = ["ALL", "HEAR", "ROUTE", "THINK", "SAY", "POINT", "SNAP", "ACT", "TTS"]
_LOG_PATH = Path.home() / ".glance" / "logs" / "session.log"


class LogsPage(BasePage):
    title = "Logs"
    icon = "📄"
    subtitle = "View, filter, and export session logs."

    def __init__(self, parent=None):
        super().__init__(parent)

        # Controls
        ctrl = QHBoxLayout()
        self._category = QComboBox()
        for cat in _CATEGORIES:
            self._category.addItem(cat)
        self._category.setStyleSheet(f"""
            QComboBox {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: {dt.INPUT_RADIUS}px;
                padding: 6px 10px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {dt.BG_CARD.name()};
                color: {dt.TEXT_PRIMARY.name()};
            }}
        """)
        self._category.currentTextChanged.connect(lambda _: self._apply_filter())
        cat_lbl = QLabel("Category:")
        cat_lbl.setFont(dt.FONT_BODY)
        cat_lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        ctrl.addWidget(cat_lbl)
        ctrl.addWidget(self._category)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs…")
        self._search.setStyleSheet(dt.LINEEDIT_QSS)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(lambda _: self._apply_filter())
        ctrl.addWidget(self._search, 1)

        export_btn = FlatButton("Export")
        export_btn.clicked.connect(self._export)
        ctrl.addWidget(export_btn)

        clear_btn = DangerButton("Clear")
        clear_btn.clicked.connect(self._clear)
        ctrl.addWidget(clear_btn)

        self.body_layout.addLayout(ctrl)

        # Viewer
        self._viewer = QTextEdit()
        self._viewer.setReadOnly(True)
        self._viewer.setFont(dt.FONT_MONO)
        self._viewer.setStyleSheet(dt.TEXTEDIT_QSS)
        self._viewer.setMinimumHeight(350)
        self.body_layout.addWidget(self._viewer, 1)

        self._all_lines: list[str] = []

    def on_activate(self):
        try:
            if _LOG_PATH.exists():
                text = _LOG_PATH.read_text(errors="replace")
                self._all_lines = text.strip().splitlines()
            else:
                self._all_lines = []
        except Exception:
            self._all_lines = []
        self._apply_filter()

    def _apply_filter(self):
        cat = self._category.currentText()
        query = self._search.text().strip().lower()
        lines = self._all_lines

        if cat != "ALL":
            lines = [l for l in lines if f"] {cat}" in l]
        if query:
            lines = [l for l in lines if query in l.lower()]

        self._viewer.setPlainText("\n".join(lines[-500:]))
        sb = self._viewer.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "glance_session.log", "Log Files (*.log *.txt)"
        )
        if path:
            try:
                Path(path).write_text(self._viewer.toPlainText())
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

    def _clear(self):
        reply = QMessageBox.question(
            self, "Clear Logs",
            "Clear the session log file? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                _LOG_PATH.write_text("")
                self._all_lines = []
                self._viewer.clear()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
