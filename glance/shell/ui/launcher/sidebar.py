"""Sidebar navigation for the launcher dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy, QSpacerItem, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from . import design_tokens as dt

NAV_SECTIONS = [
    ("LAUNCH", [
        ("home",       "Home",         "⌂"),
    ]),
    ("CONFIGURE", [
        ("api_keys",   "API Keys",     "\U0001F511"),
        ("providers",  "AI Providers", "⚙"),
        ("settings",   "Settings",     "⚙️"),
        ("models",     "Models",       "\U0001F9E0"),
        ("ollama",     "Ollama",       "\U0001F999"),
    ]),
    ("TOOLS", [
        ("extensions", "Extensions",   "\U0001F9E9"),
        ("workspace",  "Workspace",    "\U0001F4BC"),
        ("updates",    "Updates",      "⬆"),
        ("logs",       "Logs",         "\U0001F4C4"),
        ("diagnostics","Diagnostics",  "\U0001F50D"),
        ("cache",      "Cache",        "\U0001F4E6"),
    ]),
    ("DATA", [
        ("memory",     "Memory",       "\U0001F4AD"),
        ("downloads",  "Downloads",    "⬇"),
        ("security",   "Security",     "\U0001F512"),
    ]),
    ("INFO", [
        ("about",      "About",        "ℹ"),
        ("advanced",   "Advanced",     "\U0001F527"),
    ]),
]


class SidebarItem(QPushButton):
    """Single navigation item."""
    nav_clicked = pyqtSignal(str)

    def __init__(self, key: str, label: str, icon: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setText(f"  {icon}  {label}")
        self.setToolTip(label)
        self.setFont(dt.font(13))
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.clicked.connect(lambda: self.nav_clicked.emit(self.key))
        self._apply_style(False)

    def _apply_style(self, active: bool):
        bg = f"rgba(100,107,242,0.12)" if active else "transparent"
        border = f"3px solid {dt.BRAND_INDIGO.name()}" if active else "3px solid transparent"
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

        # Logo / brand
        logo_w = QWidget()
        logo_lay = QVBoxLayout(logo_w)
        logo_lay.setContentsMargins(20, 20, 20, 12)
        logo_lbl = QLabel("Glance")
        logo_lbl.setFont(dt.font(18, QFont.Weight.Bold))
        logo_lbl.setStyleSheet(f"""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()});
        """)
        logo_lbl.setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")
        logo_lay.addWidget(logo_lbl)
        sub = QLabel("Dashboard")
        sub.setFont(dt.FONT_CAPTION)
        sub.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        logo_lay.addWidget(sub)
        lay.addWidget(logo_w)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.06);")
        sep.setFixedHeight(1)
        lay.addWidget(sep)

        # Nav items (scrollable for small screens)
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
            sec.setFont(dt.font(10, QFont.Weight.DemiBold))
            sec.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; padding: 12px 0 4px 16px;")
            nav_lay.addWidget(sec)
            for key, label, icon in items:
                item = SidebarItem(key, label, icon)
                item.nav_clicked.connect(self._on_item_clicked)
                self._items[key] = item
                nav_lay.addWidget(item)

        nav_lay.addStretch()
        scroll.setWidget(nav_area)
        lay.addWidget(scroll, 1)

        # Version footer
        try:
            import glance
            ver = glance.__version__
        except Exception:
            ver = "dev"
        footer = QLabel(f"v{ver}")
        footer.setFont(dt.FONT_CAPTION)
        footer.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; padding: 8px 16px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(footer)

    def _on_item_clicked(self, key: str):
        self.set_active(key)
        self.page_selected.emit(key)

    def set_active(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)
