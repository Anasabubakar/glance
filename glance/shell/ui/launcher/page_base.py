"""Base class for every launcher page — standard header and scrollable body."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt

from . import design_tokens as dt


class BasePage(QWidget):
    """Subclass, set ``title`` and ``icon``, then add widgets to ``self.body``."""

    title: str = ""
    icon: str = ""
    subtitle: str = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 16)
        root.setSpacing(0)

        header = QWidget()
        header_lay = QVBoxLayout(header)
        header_lay.setContentsMargins(0, 0, 0, 16)
        header_lay.setSpacing(4)

        self._title_label = QLabel(f"{self.icon}  {self.title}" if self.icon else self.title)
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

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: rgba(255,255,255,0.06);")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(dt.SCROLLBAR_QSS)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 16, 0, 8)
        self.body_layout.setSpacing(16)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.body)
        root.addWidget(scroll, 1)

    def on_activate(self):
        """Called when the page becomes visible — override to refresh data."""

    # ── helpers for subclasses ───────────────────────────────────────────────

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
