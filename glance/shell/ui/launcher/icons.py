"""
icons.py — one consistent set of line icons, drawn as SVG and rendered with
QtSvg (so they are crisp at any scale and tinted to any colour).

24x24 grid, 1.8px round strokes. Usage:

    icons.pixmap("home", color="#F3F4F8", size=18)
    icons.icon("home", color=...)
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# Each value is the inner SVG (stroke-only shapes; colour is injected).
_PATHS: dict[str, str] = {
    "home": '<path d="M3 11.2 12 4l9 7.2"/><path d="M5.5 9.8V19a1 1 0 0 0 1 1H10v-5.5h4V20h3.5a1 1 0 0 0 1-1V9.8"/>',
    "ai": '<path d="M12 3.5l1.7 4.6 4.6 1.7-4.6 1.7L12 16.1l-1.7-4.6-4.6-1.7 4.6-1.7L12 3.5z"/>'
          '<path d="M18.5 15l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2z"/>',
    "cpu": '<rect x="6" y="6" width="12" height="12" rx="2.5"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/>'
           '<path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    "sliders": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    "layers": '<path d="M12 3.5 3.5 8 12 12.5 20.5 8 12 3.5z"/><path d="m3.5 12 8.5 4.5 8.5-4.5"/><path d="m3.5 16 8.5 4.5 8.5-4.5"/>',
    "activity": '<path d="M3 12h4l2.5-7 5 14L17 12h4"/>',
    "gauge": '<path d="M4.6 18a8.5 8.5 0 1 1 14.8 0"/><path d="m12 13.5 3.8-4.3"/><circle cx="12" cy="13.5" r="1" />',
    "grid": '<rect x="3.5" y="3.5" width="7" height="7" rx="1.8"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.8"/>'
            '<rect x="3.5" y="13.5" width="7" height="7" rx="1.8"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.8"/>',
    "briefcase": '<rect x="3.5" y="7.5" width="17" height="12" rx="2.2"/><path d="M9 7.5V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v1.5"/><path d="M3.5 13h17"/>',
    "download": '<path d="M12 4v11"/><path d="m7.5 11 4.5 4.5 4.5-4.5"/><path d="M5 20h14"/>',
    "database": '<ellipse cx="12" cy="6" rx="7.5" ry="2.8"/><path d="M4.5 6v6c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8V6"/><path d="M4.5 12v6c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8v-6"/>',
    "shield": '<path d="M12 3.2 19.5 6v5.6c0 4.4-3 7.7-7.5 9.2-4.5-1.5-7.5-4.8-7.5-9.2V6L12 3.2z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14-4.6L4 8.5"/><path d="M4 4v4.5h4.5"/><path d="M4 13a8 8 0 0 0 14 4.6l2-2.1"/><path d="M20 20v-4.5h-4.5"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><circle cx="12" cy="7.9" r=".6" fill="currentColor"/>',
    "terminal": '<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><path d="m7.5 10 3 2.5-3 2.5"/><path d="M13 15h3.5"/>',
    "key": '<circle cx="8" cy="15.5" r="3.8"/><path d="m10.8 12.7 8.7-8.7"/><path d="m16 7.5 2.5 2.5"/>',
    "mic": '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0"/><path d="M12 18v2.5"/>',
    "volume": '<path d="M4.5 9.8h3.2l4.8-3.8v12l-4.8-3.8H4.5z"/><path d="M16 9.2a4 4 0 0 1 0 5.6"/><path d="M18.6 6.6a7.6 7.6 0 0 1 0 10.8"/>',
    "play": '<path d="M8 5.5v13l10.5-6.5L8 5.5z"/>',
    "stop": '<rect x="6.5" y="6.5" width="11" height="11" rx="2.2"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
    "eye-off": '<path d="M4 4l16 16"/><path d="M10 6a9.5 9.5 0 0 1 2-.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-3 3.8"/><path d="M6.4 7.9A15.5 15.5 0 0 0 2.5 12S6 18.5 12 18.5c1.3 0 2.5-.3 3.6-.8"/><path d="M9.9 9.9a2.8 2.8 0 0 0 4.2 3.7"/>',
    "external": '<path d="M13 5h6v6"/><path d="M19 5 11 13"/><path d="M17 14v4a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 5 18V9a1.5 1.5 0 0 1 1.5-1.5H10"/>',
    "chevron-right": '<path d="m9.5 5.5 6 6.5-6 6.5"/>',
    "chevron-down": '<path d="m5.5 9.5 6.5 6 6.5-6"/>',
    "trash": '<path d="M4.5 7h15"/><path d="M9.5 7V4.5h5V7"/><path d="M6.5 7l.8 12a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7"/><path d="M10 11v6M14 11v6"/>',
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="2.2"/><path d="M15.5 8.5V6.2A1.7 1.7 0 0 0 13.8 4.5H6.2A1.7 1.7 0 0 0 4.5 6.2v7.6a1.7 1.7 0 0 0 1.7 1.7h2.3"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    "alert": '<path d="M12 4.2 21 19.5H3L12 4.2z"/><path d="M12 10v4.2"/><circle cx="12" cy="16.8" r=".6" fill="currentColor"/>',
    "check-circle": '<circle cx="12" cy="12" r="8.5"/><path d="m8.2 12.4 2.7 2.7 5-5.4"/>',
    "cloud": '<path d="M7 18.5a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 10.5a4 4 0 0 1-.5 8H7z"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "eye-screen": '<rect x="3" y="4.5" width="18" height="12.5" rx="2.2"/><path d="M8.5 20.5h7M12 17v3.5"/>',
    "hand": '<path d="M8 12V6.5a1.5 1.5 0 0 1 3 0V11"/><path d="M11 10.5V5a1.5 1.5 0 0 1 3 0v6"/><path d="M14 10.5V6.5a1.5 1.5 0 0 1 3 0V14c0 4-2.5 6.5-6 6.5-2.2 0-3.6-1-4.7-2.7L4 13.5a1.5 1.5 0 0 1 2.5-1.6L8 14"/>',
    "keyboard": '<rect x="2.5" y="6.5" width="19" height="11" rx="2.2"/><path d="M6.5 10.5h.01M10 10.5h.01M14 10.5h.01M17.5 10.5h.01M7.5 14h9"/>',
}

_cache: dict = {}


def names() -> list:
    return sorted(_PATHS)


def _svg(name: str, color: str, stroke: float) -> bytes:
    body = _PATHS.get(name, _PATHS["info"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body.replace("currentColor", color)}</svg>').encode()


def pixmap(name: str, color: str | QColor = "#F3F4F8", size: int = 18,
           stroke: float = 1.8, dpr: float = 2.0) -> QPixmap:
    """Render `name` as a `size`x`size` (logical px) pixmap tinted `color`."""
    col = color.name() if isinstance(color, QColor) else str(color)
    key = (name, col, size, stroke, dpr)
    pm = _cache.get(key)
    if pm is None:
        px = int(size * dpr)
        pm = QPixmap(px, px)
        pm.fill(Qt.GlobalColor.transparent)
        r = QSvgRenderer(QByteArray(_svg(name, col, stroke)))
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r.render(p)
        p.end()
        pm.setDevicePixelRatio(dpr)
        _cache[key] = pm
    return pm


def icon(name: str, color: str | QColor = "#F3F4F8", size: int = 18, stroke: float = 1.8) -> QIcon:
    return QIcon(pixmap(name, color, size, stroke))
