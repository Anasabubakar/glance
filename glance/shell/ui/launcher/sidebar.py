"""
sidebar.py — navigation. Brand on top, grouped items (real icons) in the
middle, status chip and Updates/About pinned to the bottom.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import design_tokens as dt
from . import icons
from .widgets import StatusDot

# (section label or "", [(page key, label, icon)])
NAV_SECTIONS = [
    ("", [("home", "Home", "home")]),
    ("Configure", [
        ("api_keys", "AI & Keys", "key"),
        ("models", "Models", "ai"),
        ("automations", "Automations", "activity"),
        ("settings", "Settings", "sliders"),
    ]),
    ("Your data", [
        ("memory", "Memory", "layers"),
        ("extensions", "Integrations", "grid"),
    ]),
    ("Insights", [
        ("logs", "Activity", "activity"),
        ("security", "Privacy & storage", "shield"),
    ]),
]
NAV_PINNED = [("about", "About & updates", "info")]


class SidebarItem(QPushButton):
    nav_clicked = pyqtSignal(str)

    def __init__(self, key: str, label: str, icon_name: str, parent=None):
        super().__init__(label.replace("&", "&&"), parent)
        self.key = key
        self._icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setIconSize(QSize(18, 18))
        self.setFont(dt.font(14, dt.QFont.Weight.Medium))
        self.clicked.connect(lambda: self.nav_clicked.emit(self.key))
        self._style(False)

    def _style(self, active: bool):
        color = "#8FA6FF" if active else dt.TEXT_DIM.name()
        self.setIcon(icons.icon(self._icon_name, color, 18))
        if active:
            css = (f"background: {dt.ACCENT_SOFT}; color: {dt.TEXT_PRIMARY.name()};")
        else:
            css = f"background: transparent; color: {dt.TEXT_MUTED.name()};"
        self.setStyleSheet(f"""
            QPushButton {{ {css} border: none; border-radius: 10px; text-align: left;
                           padding: 0 12px; }}
            QPushButton:hover {{ background: {dt.BG_ELEVATED.name() if not active else dt.ACCENT_SOFT};
                                 color: {dt.TEXT_PRIMARY.name()}; }}
        """)

    def set_active(self, active: bool):
        self.setChecked(active)
        self._style(active)


class Sidebar(QWidget):
    page_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(dt.SIDEBAR_WIDTH)
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"QWidget#Sidebar {{ background: {dt.SIDEBAR_BG.name()}; "
                           f"border-right: 1px solid {dt.BORDER_CSS}; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Brand ───────────────────────────────────────────────────────────
        brand = QWidget()
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(20, 22, 20, 18)
        bl.setSpacing(12)
        mark = QLabel()
        pm = dt.load_pixmap("glance-flat.png", size=34)
        if not pm.isNull():
            mark.setPixmap(pm)
        mark.setFixedSize(34, 34)
        bl.addWidget(mark)
        col = QVBoxLayout()
        col.setSpacing(0)
        name = QLabel("Glance")
        name.setFont(dt.font(19, dt.QFont.Weight.Bold))
        tag = QLabel("Your intelligent cursor")
        tag.setFont(dt.FONT_SMALL)
        tag.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        col.addWidget(name)
        col.addWidget(tag)
        bl.addLayout(col, 1)
        lay.addWidget(brand)

        # ── Scrolling nav ───────────────────────────────────────────────────
        self._items: dict[str, SidebarItem] = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(dt.SCROLLBAR_QSS + "QScrollArea > QWidget > QWidget { background: transparent; }")
        nav = QWidget()
        nl = QVBoxLayout(nav)
        nl.setContentsMargins(12, 0, 12, 12)
        nl.setSpacing(2)
        for section, items in NAV_SECTIONS:
            if section:
                sec = QLabel(section.upper())
                sec.setFont(dt.font(11, dt.QFont.Weight.DemiBold))
                sec.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; letter-spacing: 1px;")
                sec.setContentsMargins(12, 16, 0, 6)
                nl.addWidget(sec)
            for key, label, ic in items:
                self._add(nl, key, label, ic)
        nl.addStretch()
        scroll.setWidget(nav)
        lay.addWidget(scroll, 1)

        # ── Pinned footer ───────────────────────────────────────────────────
        foot = QWidget()
        fl = QVBoxLayout(foot)
        fl.setContentsMargins(12, 8, 12, 14)
        fl.setSpacing(2)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {dt.BORDER_CSS};")
        fl.addWidget(line)
        fl.addSpacing(8)
        for key, label, ic in NAV_PINNED:
            self._add(fl, key, label, ic)

        status = QWidget()
        sl = QHBoxLayout(status)
        sl.setContentsMargins(12, 10, 12, 0)
        sl.setSpacing(8)
        self._dot = StatusDot(dt.TEXT_DIM, 8)
        sl.addWidget(self._dot)
        self._status_lbl = QLabel("Not running")
        self._status_lbl.setFont(dt.FONT_CAPTION)
        self._status_lbl.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        sl.addWidget(self._status_lbl)
        sl.addStretch()
        try:
            import glance
            ver = f"v{glance.__version__}"
        except Exception:
            ver = "dev"
        v = QLabel(ver)
        v.setFont(dt.FONT_SMALL)
        v.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        sl.addWidget(v)
        fl.addWidget(status)
        lay.addWidget(foot)

    def _add(self, layout, key, label, ic):
        item = SidebarItem(key, label, ic)
        item.nav_clicked.connect(self._on_item_clicked)
        self._items[key] = item
        layout.addWidget(item)

    def _on_item_clicked(self, key: str):
        self.set_active(key)
        self.page_selected.emit(key)

    def set_active(self, key: str):
        for k, item in self._items.items():
            item.set_active(k == key)

    def set_running(self, running: bool):
        self._dot.set_color(dt.SUCCESS if running else dt.TEXT_DIM)
        self._status_lbl.setText("Glance is running" if running else "Not running")
