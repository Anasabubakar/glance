"""
Advanced page — env editor, debug toggle, reset, data directory.
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton, DangerButton, GradientButton, SettingRow
from .. import design_tokens as dt

_KNOWN_KEYS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY", "TAVILY_API_KEY",
    "GLANCE_HOTKEY", "OLLAMA_HOST", "OLLAMA_MODEL",
    "GLANCE_ACTIVE_LLM", "GLANCE_ACTIVE_MODEL",
    "GLANCE_WEB_SEARCH", "GLANCE_WAKE_WORD", "GLANCE_SLOW_MODE",
    "GLANCE_QUIZ_MODE", "GLANCE_PRIVACY", "GLANCE_CODE_MODE",
    "GLANCE_MULTILINGUAL", "GLANCE_OCR_FALLBACK", "GLANCE_JOURNAL",
    "GLANCE_DEBUG", "GLANCE_LAST_PAGE",
]


def _user_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
    return Path(os.environ.get("XDG_DATA_HOME",
                                Path.home() / ".local" / "share")) / "Glance"


class AdvancedPage(BasePage):
    title = "Advanced"
    icon = "⚡"
    subtitle = "Environment variables, debug settings, and reset options."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from config import cfg
            self._cfg = cfg
        except Exception:
            self._cfg = None

        # Debug toggle
        self.body_layout.addWidget(self.section_label("Debug"))
        debug_on = os.environ.get("GLANCE_DEBUG", "0").strip() in ("1", "true")
        self._debug_row = SettingRow(
            "Debug Logging",
            "Enable verbose debug output",
            checked=debug_on,
        )
        self._debug_row.toggled.connect(self._toggle_debug)
        self.body_layout.addWidget(self._debug_row)

        # Data directory
        self.body_layout.addWidget(self.section_label("Data Directory"))
        dir_card = Card()
        self._dir_label = QLabel(str(_user_dir()))
        self._dir_label.setFont(dt.FONT_MONO)
        self._dir_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dir_card.add_widget(self._dir_label)
        open_btn = FlatButton("Open in File Manager")
        open_btn.clicked.connect(self._open_data_dir)
        dir_card.add_widget(open_btn)
        self.body_layout.addWidget(dir_card)

        # Environment variables editor
        self.body_layout.addWidget(self.section_label("Environment Variables"))
        self.body_layout.addWidget(self.hint_label(
            "Edit Glance environment variables. Changes are saved to your .env file."
        ))

        self._table = QTableWidget(len(_KNOWN_KEYS), 2)
        self._table.setHorizontalHeaderLabels(["Variable", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {dt.BG_CARD.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: {dt.CARD_RADIUS}px;
                gridline-color: rgba(255,255,255,0.04);
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                font-size: 12px;
            }}
            QHeaderView::section {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_MUTED.name()};
                border: none;
                padding: 6px 8px;
                font-size: 11px;
            }}
        """)
        self._table.setMinimumHeight(300)
        self.body_layout.addWidget(self._table, 1)

        save_btn = GradientButton("Save All")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._save_all)
        self.body_layout.addWidget(save_btn)

        # Reset
        self.body_layout.addWidget(self.section_label("Reset"))
        reset_btn = DangerButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset)
        self.body_layout.addWidget(reset_btn)
        self.body_layout.addWidget(self.hint_label(
            "Clears your .env file and removes the setup-complete flag. "
            "Cannot be undone."
        ))
        self.body_layout.addStretch()

    def on_activate(self):
        for i, key in enumerate(_KNOWN_KEYS):
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, name_item)
            val = os.environ.get(key, "")
            if not val and self._cfg:
                attr = key.lower()
                val = getattr(self._cfg, attr, "") or ""
            val_item = QTableWidgetItem(val)
            self._table.setItem(i, 1, val_item)

    def _save_all(self):
        if not self._cfg:
            return
        values = {}
        for i in range(self._table.rowCount()):
            key_item = self._table.item(i, 0)
            val_item = self._table.item(i, 1)
            if key_item and val_item:
                values[key_item.text()] = val_item.text()
        self._cfg.save_env_values(values)
        QMessageBox.information(self, "Saved", "Environment variables saved.")

    def _toggle_debug(self, on: bool):
        os.environ["GLANCE_DEBUG"] = "1" if on else "0"
        if self._cfg:
            self._cfg._persist_env("GLANCE_DEBUG", "1" if on else "0")

    def _open_data_dir(self):
        d = _user_dir()
        d.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(d))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(d)])
        else:
            subprocess.Popen(["xdg-open", str(d)])

    def _reset(self):
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "This will clear your .env file and remove the setup-complete flag.\n\n"
            "You will need to re-enter your API keys. This cannot be undone.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            frozen = getattr(sys, "frozen", False)
            if sys.platform == "win32":
                env_path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance" / ".env"
            else:
                env_path = Path(
                    os.environ.get("XDG_DATA_HOME",
                                   Path.home() / ".local" / "share")
                ) / "Glance" / ".env"
            if not frozen:
                shell_dir = Path(__file__).parents[3]
                env_path = shell_dir / ".env"
            if env_path.exists():
                env_path.write_text("")
            setup_flag = _user_dir() / ".setup_complete"
            if setup_flag.exists():
                setup_flag.unlink()
            QMessageBox.information(self, "Reset Complete",
                                    "Glance has been reset. Restart to apply.")
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
