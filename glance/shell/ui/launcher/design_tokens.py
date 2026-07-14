"""Unified design tokens for the Glance launcher — brand palette from the
frontend globals.css merged with shell status colors."""

from PyQt6.QtGui import QColor, QFont

# ── Brand palette (from frontend/src/app/globals.css) ────────────────────────
BG_DEEP      = QColor(5, 5, 16)       # #050510
BG_SURFACE   = QColor(15, 15, 23)     # #0F0F17
BG_CARD      = QColor(20, 20, 31)     # #14141F
BG_ELEVATED  = QColor(26, 26, 46)     # #1A1A2E
BG_INPUT     = QColor(30, 30, 50)

BRAND_INDIGO = QColor(100, 107, 242)  # #646BF2
BRAND_VIOLET = QColor(140, 122, 250)  # #8C7AFA
BLUE_GLOW    = QColor(89, 140, 255)   # #598CFF

TEXT_PRIMARY = QColor(255, 255, 255)
TEXT_MUTED   = QColor(115, 115, 133)  # #737385
TEXT_DIM     = QColor(82, 82, 91)     # #52525B

BORDER_SUBTLE = QColor(255, 255, 255, 15)   # rgba(255,255,255,0.06)
BORDER_MEDIUM = QColor(255, 255, 255, 26)   # rgba(255,255,255,0.1)

# ── Status (from shell ui/design.py) ─────────────────────────────────────────
SUCCESS = QColor(74, 222, 128)   # #4ADE80
WARNING = QColor(251, 146, 60)   # #FB923C
ERROR   = QColor(255, 70, 70)

# ── Sidebar ──────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 220
SIDEBAR_BG    = BG_SURFACE

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"

def font(size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(FONT_FAMILY, size)
    f.setWeight(weight)
    return f

FONT_PAGE_TITLE   = font(20, QFont.Weight.Bold)
FONT_SECTION      = font(15, QFont.Weight.Medium)
FONT_BODY         = font(13)
FONT_CAPTION      = font(11)
FONT_MONO         = QFont("Consolas", 12)
FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)

# ── Shared stylesheet fragments ──────────────────────────────────────────────
SCROLLBAR_QSS = """
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: transparent; width: 6px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(115,115,133,80); border-radius: 3px; min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }
"""

CARD_RADIUS = 10
BUTTON_RADIUS = 8
