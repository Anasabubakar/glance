"""
design_tokens.py — Unified brand system for the Glance Desktop Launcher.

Mirrors the frontend design language (frontend/src/app/globals.css) and
integrates shell status colors. Every widget imports from here so that
changing the brand palette in one place updates the entire launcher.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt


# ── Brand Palette (from frontend/src/app/globals.css) ─────────────────────────
BG_DEEP        = QColor(5, 5, 16)          # #050510
BG_SURFACE     = QColor(15, 15, 23)        # #0F0F17
BG_CARD        = QColor(20, 20, 31)        # #14141F
BG_ELEVATED    = QColor(26, 26, 46)        # #1A1A2E
BG_INPUT       = QColor(30, 30, 50)        # custom deeper for inputs

BRAND_INDIGO   = QColor(100, 107, 242)     # #646BF2
BRAND_VIOLET   = QColor(140, 122, 250)     # #8C7AFA
BLUE_GLOW      = QColor(89, 140, 255)      # #598CFF

TEXT_PRIMARY   = QColor(255, 255, 255)     # #FFFFFF
TEXT_MUTED     = QColor(115, 115, 133)     # #737385
TEXT_DIM       = QColor(82, 82, 91)        # #52525B

BORDER_SUBTLE  = QColor(255, 255, 255, 15)  # rgba(255,255,255,0.06)
BORDER_MEDIUM  = QColor(255, 255, 255, 26)  # rgba(255,255,255,0.1)

# ── Status Colors (from shell ui/design.py) ──────────────────────────────────
SUCCESS        = QColor(74, 222, 128)      # #4ADE80
WARNING        = QColor(251, 146, 60)      # #FB923C
ERROR          = QColor(255, 70, 70)       # #FF4646
INFO           = QColor(89, 140, 255)      # #598CFF

# ── Sidebar ──────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH   = 220
SIDEBAR_BG      = BG_SURFACE

# ── Layout ───────────────────────────────────────────────────────────────────
PAGE_MARGIN_LR  = 32     # left/right margin inside each page
PAGE_MARGIN_T   = 28     # top margin
PAGE_MARGIN_B   = 16     # bottom margin
CARD_RADIUS     = 10
BUTTON_RADIUS   = 8
INPUT_RADIUS    = 6
TOGGLE_TRACK_W  = 40
TOGGLE_TRACK_H  = 22

# ── Typography ───────────────────────────────────────────────────────────────
# "Segoe UI" on Windows, "Ubuntu" / "Noto Sans" on Linux
FONT_FAMILY = "Segoe UI, Ubuntu, Noto Sans, sans-serif"

def font(size: int = 13,
         weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """Return a QFont with the project's primary family."""
    f = QFont(FONT_FAMILY.split(",")[0].strip(), size)
    f.setWeight(weight)
    return f


FONT_PAGE_TITLE  = font(22, QFont.Weight.Bold)
FONT_SECTION     = font(15, QFont.Weight.Medium)
FONT_BODY        = font(13)
FONT_CAPTION     = font(11)
FONT_MONO        = QFont("Consolas, JetBrains Mono, monospace".split(",")[0].strip(), 12)
FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
FONT_SMALL       = font(10)

# ── Logo / Brand Assets ──────────────────────────────────────────────────────
def _asset_path(*parts: str) -> str:
    """Resolve an asset relative to the launcher package, then fallback to
    the vendored shell tree, then the project root."""
    candidates = [
        Path(__file__).resolve().parent.joinpath(*parts),
        Path(__file__).resolve().parent.parent.parent.joinpath("assets", *parts),
        Path(__file__).resolve().parent.parent.parent.parent.parent.joinpath(*parts),
    ]
    for p in candidates:
        if p.is_file():
            return str(p)
    return str(candidates[0])   # return the first path even if missing


def load_pixmap(*parts: str, size: int | None = None) -> QPixmap:
    """Load a pixmap from the assets directory, optionally scaled."""
    pm = QPixmap(_asset_path(*parts))
    if not pm.isNull() and size is not None:
        pm = pm.scaled(size, size,
                       Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return pm


def load_icon(*parts: str) -> QIcon:
    """Load a QIcon from an asset path."""
    pm = load_pixmap(*parts)
    return QIcon(pm) if not pm.isNull() else QIcon()


# Convenience references — used by sidebar, window, about page
LOGO_FLAT      = _asset_path("glance-flat.png")
LOGO_3D        = _asset_path("glance.png")
CURSOR_PNG     = _asset_path("glance-cursor.png")


# ── Shared QSS Snippets ──────────────────────────────────────────────────────

SCROLLBAR_QSS = """
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical {
    background: transparent; width: 6px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(115,115,133,80); border-radius: 3px; min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(115,115,133,120);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 0; }
"""

COMBO_QSS = f"""
QComboBox {{
    background: {BG_ELEVATED.name()};
    color: {TEXT_PRIMARY.name()};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: {INPUT_RADIUS}px;
    padding: 6px 10px;
    font-size: 13px;
}}
QComboBox::drop-down {{ border: none; padding-right: 6px; }}
QComboBox::down-arrow {{
    image: none; border: none;
    width: 0; height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {TEXT_MUTED.name()};
}}
QComboBox:hover {{ border-color: {BRAND_INDIGO.name()}; }}
QComboBox QAbstractItemView {{
    background: {BG_CARD.name()};
    color: {TEXT_PRIMARY.name()};
    border: 1px solid {BORDER_MEDIUM.name()};
    border-radius: 4px;
    selection-background-color: rgba(100,107,242,0.2);
    outline: none;
}}
"""

LINEEDIT_QSS = f"""
QLineEdit {{
    background: {BG_ELEVATED.name()};
    color: {TEXT_PRIMARY.name()};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: {INPUT_RADIUS}px;
    padding: 8px 10px;
    font-size: 13px;
}}
QLineEdit:focus {{
    border-color: {BRAND_INDIGO.name()};
}}
QLineEdit::placeholder {{ color: {TEXT_DIM.name()}; }}
"""

TEXTEDIT_QSS = f"""
QTextEdit {{
    background: {BG_CARD.name()};
    color: {TEXT_MUTED.name()};
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: {CARD_RADIUS}px;
    padding: 10px;
    font-size: 12px;
}}
QTextEdit:focus {{ border-color: {BRAND_INDIGO.name()}; }}
"""
