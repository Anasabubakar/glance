"""
design_tokens.py — the Glance design system (single source of truth).

Every colour, size and style in the desktop app comes from here, so changing the
look means changing this file. Principles:

  * calm, near-black surfaces with ONE accent; status colours only for status
  * a strict 4-px spacing scale and three radii (card / control / pill)
  * 1-px hairline borders instead of shadows (shadows render badly in Qt)
  * a real type scale in pixels, set by role (title / section / body / caption)

Names used by older pages (BG_*, TEXT_*, FONT_*, ..._QSS) are kept, but their
values are the new design.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPixmap


def _hex(c: QColor) -> str:
    return c.name()


# ── Colour ───────────────────────────────────────────────────────────────────
# Surfaces step up in lightness: app < sidebar < card < raised < input.
BG_DEEP      = QColor("#0B0C10")      # app background
BG_SURFACE   = QColor("#0F1015")      # sidebar
BG_CARD      = QColor("#14161D")      # cards
BG_ELEVATED  = QColor("#1B1E27")      # raised controls, hover
BG_INPUT     = QColor("#0E0F14")      # inputs sit *below* the card
BG_HOVER     = QColor("#191C24")

# One accent. Soft tint is for selected / active backgrounds.
BRAND_INDIGO = QColor("#5B7CFF")      # accent
BRAND_VIOLET = QColor("#7C6CFF")      # accent, gradient partner (CTA only)
BLUE_GLOW    = QColor("#6E8BFF")
ACCENT_HOVER = QColor("#7391FF")
ACCENT_SOFT  = "rgba(91,124,255,0.14)"
ACCENT_LINE  = "rgba(91,124,255,0.45)"

TEXT_PRIMARY = QColor("#F3F4F8")
TEXT_MUTED   = QColor("#A3A8BA")      # secondary text (descriptions)
TEXT_DIM     = QColor("#6B7083")      # tertiary (captions, placeholders)

BORDER_SUBTLE = QColor(255, 255, 255, 18)    # hairline
BORDER_MEDIUM = QColor(255, 255, 255, 30)
BORDER_CSS        = "rgba(255,255,255,0.07)"
BORDER_STRONG_CSS = "rgba(255,255,255,0.13)"

# Status — used only to communicate status.
SUCCESS = QColor("#3DD68C")
WARNING = QColor("#F5A524")
ERROR   = QColor("#F5616A")
INFO    = QColor("#6E8BFF")

# ── Layout ───────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH  = 244
SIDEBAR_BG     = BG_SURFACE
CONTENT_MAX_W  = 880          # readable column width
PAGE_MARGIN_LR = 40
PAGE_MARGIN_T  = 36
PAGE_MARGIN_B  = 24

CARD_RADIUS    = 14
BUTTON_RADIUS  = 10
INPUT_RADIUS   = 10
PILL_RADIUS    = 999

# 4-px spacing scale
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6, SP_8 = 4, 8, 12, 16, 20, 24, 32

TOGGLE_TRACK_W = 42
TOGGLE_TRACK_H = 24

# ── Typography (pixels) ──────────────────────────────────────────────────────
_FAMILIES = ["Inter", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI",
             "Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans"]
FONT_STACK_CSS = ('"Inter", "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", '
                  '"Cantarell", "Ubuntu", "Noto Sans", sans-serif')
MONO_STACK_CSS = '"JetBrains Mono", "Cascadia Mono", "Ubuntu Mono", "DejaVu Sans Mono", monospace'
FONT_FAMILY = FONT_STACK_CSS          # legacy name

_family_cache: str | None = None


def _family() -> str:
    """First installed family from the preference list (resolved once)."""
    global _family_cache
    if _family_cache is None:
        from PyQt6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:       # fonts can't be queried without an app
            return "Sans Serif"                       # (not cached: retry once the app exists)
        try:
            have = set(QFontDatabase.families())
            _family_cache = next((f for f in _FAMILIES if f in have), "Sans Serif")
        except Exception:
            _family_cache = "Sans Serif"
    return _family_cache


def font(size: int = 14, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    """A QFont of `size` PIXELS in the app font."""
    f = QFont(_family())
    f.setPixelSize(int(size))
    f.setWeight(weight)
    return f


_W = QFont.Weight
FONT_PAGE_TITLE = font(26, _W.DemiBold)
FONT_SECTION    = font(12, _W.DemiBold)      # small-caps section label
FONT_BODY       = font(14)
FONT_CAPTION    = font(12)
FONT_SMALL      = font(11)
FONT_MONO       = QFont("monospace")
FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
FONT_MONO.setPixelSize(12)


# ── Assets ───────────────────────────────────────────────────────────────────
def _asset_path(*parts: str) -> str:
    """Resolve an asset relative to the launcher package, then the shell assets,
    then the project root."""
    base = Path(__file__).resolve().parent
    for p in (base.joinpath(*parts),
              base.parent.parent.joinpath("assets", *parts),
              base.parent.parent.parent.parent.joinpath(*parts)):
        if p.is_file():
            return str(p)
    return str(base.joinpath(*parts))


def load_pixmap(*parts: str, size: int | None = None) -> QPixmap:
    pm = QPixmap(_asset_path(*parts))
    if not pm.isNull() and size is not None:
        pm = pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return pm


def load_icon(*parts: str) -> QIcon:
    pm = load_pixmap(*parts)
    return QIcon(pm) if not pm.isNull() else QIcon()


LOGO_FLAT  = _asset_path("glance-flat.png")
LOGO_3D    = _asset_path("glance.png")
CURSOR_PNG = _asset_path("glance-cursor.png")


# ── Shared QSS snippets ──────────────────────────────────────────────────────
SCROLLBAR_QSS = """
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px 4px 0; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); border-radius: 3px;
                              min-height: 32px; margin: 0 2px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.22); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { height: 0; }
"""

LINEEDIT_QSS = f"""
QLineEdit {{
    background: {_hex(BG_INPUT)}; color: {_hex(TEXT_PRIMARY)};
    border: 1px solid {BORDER_CSS}; border-radius: {INPUT_RADIUS}px;
    padding: 0 12px; min-height: 38px; font-size: 14px;
    selection-background-color: {ACCENT_LINE};
}}
QLineEdit:hover {{ border-color: {BORDER_STRONG_CSS}; }}
QLineEdit:focus {{ border: 1px solid {_hex(BRAND_INDIGO)}; }}
"""

COMBO_QSS = f"""
QComboBox {{
    background: {_hex(BG_INPUT)}; color: {_hex(TEXT_PRIMARY)};
    border: 1px solid {BORDER_CSS}; border-radius: {INPUT_RADIUS}px;
    padding: 0 12px; min-height: 38px; font-size: 14px;
}}
QComboBox:hover {{ border-color: {BORDER_STRONG_CSS}; }}
QComboBox:focus {{ border-color: {_hex(BRAND_INDIGO)}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}

QComboBox QAbstractItemView {{
    background: {_hex(BG_ELEVATED)}; color: {_hex(TEXT_PRIMARY)};
    border: 1px solid {BORDER_STRONG_CSS}; border-radius: 8px; padding: 4px; outline: none;
    selection-background-color: {ACCENT_SOFT}; selection-color: {_hex(TEXT_PRIMARY)};
}}
"""

TEXTEDIT_QSS = f"""
QTextEdit, QPlainTextEdit {{
    background: {_hex(BG_INPUT)}; color: {_hex(TEXT_MUTED)};
    border: 1px solid {BORDER_CSS}; border-radius: {INPUT_RADIUS}px;
    padding: 12px; font-size: 12px; font-family: {MONO_STACK_CSS};
    selection-background-color: {ACCENT_LINE};
}}
QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {_hex(BRAND_INDIGO)}; }}
"""

def arrow_qss() -> str:
    """Combo-box chevron: Qt can't draw one in QSS, so render icons.py's chevron to a
    PNG in the temp dir and point the stylesheet at it. Call after the app exists."""
    import tempfile
    from . import icons
    d = Path(tempfile.gettempdir()) / "glance-ui"
    d.mkdir(exist_ok=True)
    f = d / "chevron-down.png"
    icons.pixmap("chevron-down", TEXT_MUTED, 16, dpr=1.0).save(str(f))
    return (f'QComboBox::down-arrow {{ image: url("{f.as_posix()}"); width: 16px; height: 16px; '
            f'margin-right: 8px; }}')


# Applied once to the whole launcher window. The first rule is the important one:
# a QLabel must never paint its own background (that was the black-box bug).
APP_QSS = f"""
* {{ font-family: {FONT_STACK_CSS}; }}
QWidget {{ color: {_hex(TEXT_PRIMARY)}; }}
QLabel {{ background: transparent; border: none; }}
QCheckBox {{ background: transparent; spacing: 8px; }}
QToolTip {{
    background: {_hex(BG_ELEVATED)}; color: {_hex(TEXT_PRIMARY)};
    border: 1px solid {BORDER_STRONG_CSS}; border-radius: 8px; padding: 6px 10px; font-size: 12px;
}}
QMessageBox, QDialog {{ background: {_hex(BG_CARD)}; }}
QMessageBox QLabel {{ color: {_hex(TEXT_PRIMARY)}; }}
QMessageBox QPushButton {{
    background: {_hex(BG_ELEVATED)}; color: {_hex(TEXT_PRIMARY)};
    border: 1px solid {BORDER_STRONG_CSS}; border-radius: {BUTTON_RADIUS}px;
    padding: 0 18px; min-height: 34px; min-width: 70px;
}}
QMessageBox QPushButton:hover {{ background: {_hex(BG_HOVER)}; }}
{SCROLLBAR_QSS}
{LINEEDIT_QSS}
{COMBO_QSS}
{TEXTEDIT_QSS}
"""
