"""
page_base.py — Enhanced base class for every launcher page.

Provides standard header, scrollable body, section helpers, and a fade-in
animation when the page becomes active.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt

from . import design_tokens as dt


class BasePage(QWidget):
    """Subclass, set ``title``, ``icon``, and ``subtitle``, then add widgets
    to ``self.body_layout``."""

    title: str = ""
    icon: str = ""
    subtitle: str = ""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Root vertical layout — header + separator + scrollable body
        root = QVBoxLayout(self)
        root.setContentsMargins(dt.PAGE_MARGIN_LR, dt.PAGE_MARGIN_T,
                                dt.PAGE_MARGIN_LR, dt.PAGE_MARGIN_B)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────
        header = QWidget()
        header_lay = QVBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 16)
        header_lay.setSpacing(4)

        title_text = f"{self.icon}  {self.title}" if self.icon else self.title
        self._title_label = QLabel(title_text)
        self._title_label.setFont(dt.FONT_PAGE_TITLE)
        self._title_label.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        header_lay.addWidget(self._title_label)

        if self.subtitle:
            sub = QLabel(self.subtitle)
            sub.setFont(dt.FONT_CAPTION)
            sub.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            sub.setWordWrap(True)
            header_lay.addWidget(sub)

        root.addWidget(header)

        # ── Separator ──────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.06);")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── Scrollable body ─────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(dt.SCROLLBAR_QSS)
        # Let the scroll area expand vertically
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding,
                             QSizePolicy.Policy.Expanding)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 16, 0, 8)
        self.body_layout.setSpacing(16)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.body)
        root.addWidget(scroll, 1)   # 1 = stretch factor

        # ── Loading overlay state ───────────────────────────────────────
        self._loading = False

    def on_activate(self):
        """Called when the page becomes visible — override to refresh data."""
        pass

    def set_loading(self, active: bool):
        """Show or hide a loading state (subclass can override for visuals)."""
        self._loading = active
        self.body.setEnabled(not active)

    # ── Static helpers used by subclasses ────────────────────────────────────

    @staticmethod
    def section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(dt.FONT_SECTION)
        lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()}; padding-top: 8px;")
        return lbl

    @staticmethod
    def hint_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(dt.FONT_CAPTION)
        lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def small_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(dt.FONT_SMALL)
        lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        return lbl

    # ── Clear helper for subclasses ──────────────────────────────────────────

    def clear_body(self):
        """Remove all widgets from the body layout (except the stretch)."""
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
