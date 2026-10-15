"""
page_base.py — the template every dashboard page is built on.

A header (icon tile, title, subtitle, optional actions) above a scrolling body
that is a single centred column of readable width. Pages only add widgets to
``self.body_layout``; spacing, margins and typography come from here.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from . import design_tokens as dt
from . import icons
from .widgets import IconTile


class BasePage(QWidget):
    """Subclass, set ``title``, ``icon`` (an icons.py name) and ``subtitle``."""

    title: str = ""
    icon: str = "info"
    subtitle: str = ""

    _embed_next = False

    @classmethod
    def embedded(cls, *args, **kwargs):
        """Build this page WITHOUT its own header/scroll, to live inside a hub tab."""
        BasePage._embed_next = True
        try:
            return cls(*args, **kwargs)
        finally:
            BasePage._embed_next = False

    def __init__(self, parent=None):
        super().__init__(parent)
        if BasePage._embed_next:
            BasePage._embed_next = False
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            self.header_actions = QHBoxLayout()
            self.body = QWidget()
            self.body_layout = QVBoxLayout(self.body)
            self.body_layout.setContentsMargins(0, 0, 0, 0)
            self.body_layout.setSpacing(16)
            self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            root.addWidget(self.body)
            self._title_label = None
            self._loading = False
            return
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header (full width, content-width inner column) ─────────────────
        header_wrap = QWidget()
        hw = QHBoxLayout(header_wrap)
        hw.setContentsMargins(dt.PAGE_MARGIN_LR, dt.PAGE_MARGIN_T, dt.PAGE_MARGIN_LR, 20)
        hw.addStretch(1)
        header = QWidget()
        header.setMaximumWidth(dt.CONTENT_MAX_W)
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(16)
        name = self.icon if self.icon in icons.names() else "info"
        hl.addWidget(IconTile(name, 44), 0, Qt.AlignmentFlag.AlignTop)
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self._title_label = QLabel(self.title)
        self._title_label.setFont(dt.FONT_PAGE_TITLE)
        text_col.addWidget(self._title_label)
        if self.subtitle:
            sub = QLabel(self.subtitle)
            sub.setFont(dt.font(14))
            sub.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            sub.setWordWrap(True)
            text_col.addWidget(sub)
        hl.addLayout(text_col, 1)
        # Optional right-aligned actions: pages add buttons to this layout.
        self.header_actions = QHBoxLayout()
        self.header_actions.setSpacing(8)
        hl.addLayout(self.header_actions)
        hw.addWidget(header, 100)
        hw.addStretch(1)
        root.addWidget(header_wrap)

        # ── Scrolling body ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(dt.SCROLLBAR_QSS + "QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        canvas = QWidget()
        cl = QHBoxLayout(canvas)
        cl.setContentsMargins(dt.PAGE_MARGIN_LR, 0, dt.PAGE_MARGIN_LR, dt.PAGE_MARGIN_B)
        cl.addStretch(1)
        self.body = QWidget()
        self.body.setMaximumWidth(dt.CONTENT_MAX_W)
        self.body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(16)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        cl.addWidget(self.body, 100)
        cl.addStretch(1)
        scroll.setWidget(canvas)
        root.addWidget(scroll, 1)

        self._loading = False

    def on_activate(self):
        """Called when the page becomes visible — override to refresh data."""

    def set_loading(self, active: bool):
        self._loading = active
        self.body.setEnabled(not active)

    # ── Helpers used by pages ────────────────────────────────────────────────
    @staticmethod
    def section_label(text: str) -> QLabel:
        """Section heading above a group of cards."""
        lbl = QLabel(text)
        lbl.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        lbl.setContentsMargins(0, 10, 0, 0)
        return lbl

    @staticmethod
    def hint_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(dt.font(13))
        lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def small_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(dt.FONT_SMALL)
        lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        return lbl

    def clear_body(self):
        from .widgets import _clear_layout
        _clear_layout(self.body_layout)
