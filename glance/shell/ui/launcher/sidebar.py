"""
sidebar.py — Premium navigation sidebar with integrated Glance branding.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QLinearGradient, QBrush

from . import design_tokens as dt
from .widgets import PillBadge


NAV_SECTIONS = [
    ("LAUNCH", [
        ("home",       "Home",         "⏎"),
    ]),
    ("CONFIGURE", [
        ("api_keys",   "API Keys",     "🔑"),
        ("providers",  "AI Providers", "⚙"),
        ("settings",   "Settings",     "⚙"),
        ("models",     "Models",       "🧠"),
        ("ollama",     "Ollama",       "🦙"),
    ]),
    ("TOOLS", [
        ("extensions", "Extensions",   "🧩"),
        ("workspace",  "Workspace",    "💼"),
        ("updates",    "Updates",      "⬆"),
        ("logs",       "Logs",         "📄"),
        ("diagnostics","Diagnostics",  "🔍"),
        ("cache",      "Cache",        "📦"),
    ]),
    ("DATA", [
        ("memory",     "Memory",       "💭"),
        ("downloads",  "Downloads",    "⬇"),
        ("security",   "Security",     "🔒"),
    ]),
    ("INFO", [
        ("about",      "About",        "ℹ"),
        ("advanced",   "Advanced",     "⚡"),
    ]),
]


class SidebarItem(QPushButton):
    """Single navigation item with active indicator."""
    nav_clicked = pyqtSignal(str)

    def __init__(self, key: str, label: str, icon: str, parent=None):
        super().__init__(parent)
        self.key = key
        self._icon = icon
        self._label = label
        self.setText(f"  {icon}  {label}")
        self.setToolTip(label)
        self.setFont(dt.font(13))
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.clicked.connect(lambda: self.nav_clicked.emit(self.key))
        self._apply_style(False)

    def _apply_style(self, active: bool):
        bg = "rgba(100,107,242,0.12)" if active else "transparent"
        border = (
            f"3px solid {dt.BRAND_INDIGO.name()}" if active
            else "3px solid transparent"
        )
        text_c = dt.TEXT_PRIMARY.name() if active else dt.TEXT_MUTED.name()
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {text_c};
                border: none;
                border-left: {border};
                text-align: left;
                padding-left: 12px;
                border-radius: 0;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: rgba(100,107,242,0.08);
                color: {dt.TEXT_PRIMARY.name()};
            }}
        """)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._apply_style(active)


class Sidebar(QWidget):
    page_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(dt.SIDEBAR_WIDTH)
        self.setStyleSheet(f"background: {dt.SIDEBAR_BG.name()};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Brand header ────────────────────────────────────────────────
        logo_w = QWidget()
        logo_lay = QVBoxLayout(logo_w)
        logo_lay.setContentsMargins(16, 16, 16, 12)
        logo_lay.setSpacing(0)

        # Logo + title in a horizontal row
        brand_row = QWidget()
        brand_lay = QVBoxLayout(brand_row)
        brand_lay.setContentsMargins(0, 0, 0, 0)
        brand_lay.setSpacing(0)

        # Glance brand mark
        brand_top = QWidget()
        brand_top_lay = QVBoxLayout(brand_top)
        brand_top_lay.setContentsMargins(0, 0, 0, 0)
        brand_top_lay.setSpacing(2)

        # Try to load the flat logo
        logo_pm = dt.load_pixmap("glance-flat.png", size=28)
        if not logo_pm.isNull():
            logo_lbl = QLabel()
            logo_lbl.setPixmap(logo_pm)
            logo_lbl.setFixedSize(28, 28)
        else:
            logo_lbl = QLabel("G")
            logo_lbl.setFont(dt.font(24, dt.QFont.Weight.Bold))
            logo_lbl.setStyleSheet(
                f"color: {dt.BRAND_INDIGO.name()};"
            )

        name_lbl = QLabel("Glance")
        name_lbl.setFont(dt.font(20, dt.QFont.Weight.Bold))
        # Gradient text via stylesheet isn't well-supported in Qt, use solid
        name_lbl.setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")

        subtitle = QLabel("AI Desktop Companion")
        subtitle.setFont(dt.FONT_SMALL)
        subtitle.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; letter-spacing: 0.5px;")
        subtitle.setContentsMargins(0, 0, 0, 0)

        logo_lay.addWidget(logo_lbl)
        logo_lay.addWidget(name_lbl)
        logo_lay.addWidget(subtitle)

        lay.addWidget(logo_w)

        # ── Separator ───────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.06);")
        sep.setFixedHeight(1)
        lay.addWidget(sep)

        # ── Navigation items (scrollable) ───────────────────────────────
        self._items: dict[str, SidebarItem] = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 4px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(115,115,133,60); border-radius: 2px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        nav_area = QWidget()
        nav_lay = QVBoxLayout(nav_area)
        nav_lay.setContentsMargins(8, 8, 8, 8)
        nav_lay.setSpacing(1)

        for section_label, items in NAV_SECTIONS:
            sec = QLabel(section_label)
            sec.setFont(dt.font(10, dt.QFont.Weight.DemiBold))
            sec.setStyleSheet(
                f"color: {dt.TEXT_DIM.name()}; padding: 12px 0 4px 16px; "
                "letter-spacing: 1px;"
            )
            nav_lay.addWidget(sec)

            for key, label, icon in items:
                item = SidebarItem(key, label, icon)
                item.nav_clicked.connect(self._on_item_clicked)
                self._items[key] = item
                nav_lay.addWidget(item)

        nav_lay.addStretch()
        scroll.setWidget(nav_area)
        lay.addWidget(scroll, 1)

        # ── Footer with version ─────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(40)
        footer_lay = QVBoxLayout(footer)
        footer_lay.setContentsMargins(16, 6, 16, 6)
        footer_lay.setSpacing(0)

        try:
            import glance
            ver = glance.__version__
        except Exception:
            ver = "dev"

        ver_lbl = QLabel(f"v{ver}")
        ver_lbl.setFont(dt.FONT_SMALL)
        ver_lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_lay.addWidget(ver_lbl)

        lay.addWidget(footer)

    def _on_item_clicked(self, key: str):
        self.set_active(key)
        self.page_selected.emit(key)

    def set_active(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)
