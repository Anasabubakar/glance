"""Cache page — model cache files, per-provider clear, total size."""

import os
import sys
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton, DangerButton
from .. import design_tokens as dt


def _cache_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Glance"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Glance"


class CachePage(BasePage):
    title = "Cache"
    icon = "\U0001F4E6"
    subtitle = "Manage model cache files and free disk space."

    def __init__(self, parent=None):
        super().__init__(parent)

        self.body_layout.addWidget(self.section_label("Cache Summary"))
        self._summary_card = Card()
        self._total_label = QLabel("Calculating…")
        self._total_label.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
        self._total_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        self._summary_card.add_widget(self._total_label)

        self._dir_label = QLabel("")
        self._dir_label.setFont(dt.FONT_CAPTION)
        self._dir_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._dir_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._summary_card.add_widget(self._dir_label)
        self.body_layout.addWidget(self._summary_card)

        self.body_layout.addWidget(self.section_label("Cache Files"))
        self._files_container = QVBoxLayout()
        self._files_container.setSpacing(6)
        self.body_layout.addLayout(self._files_container)

        btn_row = QHBoxLayout()
        clear_all = DangerButton("Clear All Cache")
        clear_all.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_all)
        btn_row.addStretch()
        self.body_layout.addLayout(btn_row)

        self.body_layout.addStretch()

    def on_activate(self):
        cdir = _cache_dir()
        self._dir_label.setText(str(cdir))

        while self._files_container.count():
            item = self._files_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cache_files = sorted(cdir.glob("models_*.json")) if cdir.exists() else []
        total = 0

        if not cache_files:
            lbl = QLabel("No cache files found.")
            lbl.setFont(dt.FONT_CAPTION)
            lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            self._files_container.addWidget(lbl)
        else:
            for f in cache_files:
                size = f.stat().st_size
                total += size
                card = Card()
                row = QHBoxLayout()
                name = QLabel(f.name)
                name.setFont(dt.FONT_BODY)
                name.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
                row.addWidget(name, 1)
                size_lbl = QLabel(f"{size / 1024:.1f} KB")
                size_lbl.setFont(dt.FONT_CAPTION)
                size_lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
                row.addWidget(size_lbl)
                del_btn = FlatButton("Delete")
                del_btn.setFixedWidth(70)
                del_btn.clicked.connect(lambda _c=False, p=f: self._delete_file(p))
                row.addWidget(del_btn)
                card.add_layout(row)

                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                age = QLabel(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M')}")
                age.setFont(dt.FONT_CAPTION)
                age.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
                card.add_widget(age)

                self._files_container.addWidget(card)

        self._total_label.setText(f"Total cache: {total / 1024:.1f} KB ({len(cache_files)} files)")

    def _delete_file(self, path: Path):
        reply = QMessageBox.question(
            self, "Delete Cache File",
            f"Delete {path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                path.unlink()
            except Exception:
                pass
            self.on_activate()

    def _clear_all(self):
        reply = QMessageBox.question(
            self, "Clear All Cache",
            "Delete all model cache files? Models will be re-fetched on next use.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cdir = _cache_dir()
            for f in cdir.glob("models_*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass
            self.on_activate()
