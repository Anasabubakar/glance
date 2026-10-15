"""
widgets.py — the Glance component library.

Every control in the dashboard comes from here, built on design_tokens and
icons. No drop shadows or graphics effects (they caused the black label boxes);
depth comes from surface lightness and 1-px hairlines.

Existing class names are kept (Card, ToggleSwitch, KeyField, GradientButton,
FlatButton, DangerButton, IconButton, PillBadge, SearchField, SettingRow,
StatCard, ProgressCard, StatusDot, LoadingSpinner) so older pages keep working;
new building blocks: Divider, Banner, IconTile, SettingsGroup, SectionHeader.
"""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QRectF, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from . import design_tokens as dt
from . import icons

_ACCENT = dt.BRAND_INDIGO.name()


# ═════════════════════════════════════════════════════════════════════════════
#  Primitives
# ═════════════════════════════════════════════════════════════════════════════

class LoadingSpinner(QWidget):
    """Smooth spinning arc, accent coloured."""

    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(16)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 9) % 360
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(dt.BRAND_INDIGO)
        pen.setWidthF(2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(3, 3, self.width() - 6, self.height() - 6), -self._angle * 16, 270 * 16)
        p.end()


class StatusDot(QWidget):
    """Filled circle with a soft halo — success / warning / error / idle."""

    def __init__(self, color: QColor = dt.TEXT_DIM, size: int = 8, parent=None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size + 6, size + 6)

    def set_color(self, color: QColor):
        self._color = color
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        halo = QColor(self._color)
        halo.setAlpha(46)
        p.setBrush(QBrush(halo))
        p.drawEllipse(0, 0, self.width(), self.height())
        p.setBrush(QBrush(self._color))
        o = (self.width() - self._size) / 2
        p.drawEllipse(QRectF(o, o, self._size, self._size))
        p.end()


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {dt.BORDER_CSS}; border: none;")


class IconTile(QLabel):
    """Rounded square holding an icon — used for page headers and tiles."""

    def __init__(self, name: str, size: int = 40, color: QColor | str = _ACCENT,
                 bg: str = dt.ACCENT_SOFT, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPixmap(icons.pixmap(name, color, int(size * 0.5)))
        self.setStyleSheet(f"background: {bg}; border-radius: {int(size * 0.3)}px;")


# ═════════════════════════════════════════════════════════════════════════════
#  Card
# ═════════════════════════════════════════════════════════════════════════════

class Card(QFrame):
    """Surface container: card background, hairline border, 14px radius."""

    def __init__(self, parent=None, hoverable: bool = False, padding: int = 20):
        super().__init__(parent)
        self.setObjectName("Card")
        self._hoverable = hoverable
        self._apply(False)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding - 2, padding, padding - 2)
        self._layout.setSpacing(12)
        if hoverable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _apply(self, hover: bool):
        border = dt.BORDER_STRONG_CSS if hover else dt.BORDER_CSS
        bg = dt.BG_HOVER.name() if hover else dt.BG_CARD.name()
        self.setStyleSheet(
            f"QFrame#Card {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: {dt.CARD_RADIUS}px; }}")

    def enterEvent(self, _ev):
        if self._hoverable:
            self._apply(True)

    def leaveEvent(self, _ev):
        if self._hoverable:
            self._apply(False)

    def add_widget(self, w: QWidget):
        self._layout.addWidget(w)

    def add_layout(self, lay):
        self._layout.addLayout(lay)

    def clear_layout(self):
        _clear_layout(self._layout)


def _clear_layout(layout) -> None:
    """Delete every widget AND nested layout, hiding at once so a re-render
    never shows old rows under the new ones."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())
            item.layout().deleteLater()


# ═════════════════════════════════════════════════════════════════════════════
#  Buttons
# ═════════════════════════════════════════════════════════════════════════════

def _btn_common(btn: QPushButton, icon_name: str | None, icon_color: str, height: int):
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(height)
    btn.setFont(dt.font(14, dt.QFont.Weight.Medium) if hasattr(dt, "QFont") else btn.font())
    if icon_name:
        btn.setIcon(icons.icon(icon_name, icon_color, 18))
        btn.setIconSize(QSize(18, 18))


class GradientButton(QPushButton):
    """Primary action — the single most important button on a screen."""

    def __init__(self, text: str, parent=None, icon: str | None = None):
        super().__init__(text.replace("&", "&&"), parent)
        _btn_common(self, icon, "#FFFFFF", 42)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()});
                color: white; border: none; border-radius: {dt.BUTTON_RADIUS}px;
                padding: 0 22px; font-weight: 600;
            }}
            QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 {dt.ACCENT_HOVER.name()}, stop:1 #9285FF); }}
            QPushButton:pressed {{ background: {dt.BRAND_INDIGO.name()}; }}
            QPushButton:disabled {{ background: {dt.BG_ELEVATED.name()}; color: {dt.TEXT_DIM.name()}; }}
        """)


class FlatButton(QPushButton):
    """Secondary action."""

    def __init__(self, text: str, parent=None, icon: str | None = None):
        super().__init__(text.replace("&", "&&"), parent)
        _btn_common(self, icon, dt.TEXT_PRIMARY.name(), 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {dt.BG_ELEVATED.name()}; color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid {dt.BORDER_CSS}; border-radius: {dt.BUTTON_RADIUS}px;
                padding: 0 16px; font-weight: 500;
            }}
            QPushButton:hover {{ background: {dt.BG_HOVER.name()}; border-color: {dt.BORDER_STRONG_CSS}; }}
            QPushButton:pressed {{ background: {dt.BG_INPUT.name()}; }}
            QPushButton:disabled {{ color: {dt.TEXT_DIM.name()}; background: transparent; }}
        """)


class GhostButton(QPushButton):
    """Tertiary / text-only action."""

    def __init__(self, text: str, parent=None, icon: str | None = None):
        super().__init__(text.replace("&", "&&"), parent)
        _btn_common(self, icon, dt.TEXT_MUTED.name(), 34)
        self.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {dt.TEXT_MUTED.name()}; border: none;
                           border-radius: {dt.BUTTON_RADIUS}px; padding: 0 12px; font-weight: 500; }}
            QPushButton:hover {{ background: {dt.BG_ELEVATED.name()}; color: {dt.TEXT_PRIMARY.name()}; }}
            QPushButton:disabled {{ color: {dt.TEXT_DIM.name()}; }}
        """)


class DangerButton(QPushButton):
    def __init__(self, text: str, parent=None, icon: str | None = None):
        super().__init__(text.replace("&", "&&"), parent)
        _btn_common(self, icon, dt.ERROR.name(), 36)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(245,97,106,0.10); color: {dt.ERROR.name()};
                border: 1px solid rgba(245,97,106,0.28); border-radius: {dt.BUTTON_RADIUS}px;
                padding: 0 16px; font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(245,97,106,0.18); }}
            QPushButton:disabled {{ color: {dt.TEXT_DIM.name()}; border-color: {dt.BORDER_CSS}; background: transparent; }}
        """)


class IconButton(QPushButton):
    """Square, icon-only. `text` may be an icon NAME (preferred) or a glyph."""

    def __init__(self, text: str = "", tooltip: str = "", parent=None, icon: str | None = None):
        name = icon or (text if text in icons.names() else None)
        super().__init__("" if name else text, parent)
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        if name:
            self.setIcon(icons.icon(name, dt.TEXT_MUTED.name(), 18))
            self.setIconSize(QSize(18, 18))
        self.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {dt.TEXT_MUTED.name()}; border: none;
                           border-radius: {dt.BUTTON_RADIUS}px; font-size: 14px; }}
            QPushButton:hover {{ background: {dt.BG_ELEVATED.name()}; color: {dt.TEXT_PRIMARY.name()}; }}
        """)


# ═════════════════════════════════════════════════════════════════════════════
#  Toggle
# ═════════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = bool(checked)
        self._pos = 1.0 if checked else 0.0          # 0..1 thumb position
        self.setFixedSize(dt.TOGGLE_TRACK_W, dt.TOGGLE_TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, on: bool, animate: bool = True):
        on = bool(on)
        if on == self._checked:
            return
        self._checked = on
        self._go(animate)

    def _go(self, animate: bool):
        target = 1.0 if self._checked else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._pos = target
            self.update()

    def mousePressEvent(self, _ev):
        self._checked = not self._checked
        self._go(True)
        self.toggled.emit(self._checked)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        off, on = QColor(58, 62, 78), dt.BRAND_INDIGO
        t = self._pos
        track = QColor(int(off.red() + (on.red() - off.red()) * t),
                       int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        d = h - 6
        x = 3 + (w - d - 6) * t
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()


# ═════════════════════════════════════════════════════════════════════════════
#  Badges, inputs
# ═════════════════════════════════════════════════════════════════════════════

class PillBadge(QLabel):
    """Small status pill. Variants: default, success, warning, error, info, accent."""

    _VARIANTS = {
        "default": ("rgba(255,255,255,0.07)", dt.TEXT_MUTED.name()),
        "success": ("rgba(61,214,140,0.14)", dt.SUCCESS.name()),
        "warning": ("rgba(245,165,36,0.14)", dt.WARNING.name()),
        "error":   ("rgba(245,97,106,0.14)", dt.ERROR.name()),
        "info":    ("rgba(110,139,255,0.15)", "#8FA6FF"),
        "accent":  (dt.ACCENT_SOFT, "#8FA6FF"),
    }

    def __init__(self, text: str, variant: str = "default", parent=None):
        super().__init__(text, parent)
        self.set_variant(variant)

    def set_variant(self, variant: str):
        self._bg, self._fg = self._VARIANTS.get(variant, self._VARIANTS["default"])
        self._radius = 8
        self._restyle()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def _restyle(self):
        self.setStyleSheet(
            f"background: {self._bg}; color: {self._fg}; border-radius: {self._radius}px; "
            f"padding: 3px 11px; font-size: 12px; font-weight: 600;")

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        r = max(4, self.height() // 2 - 1)           # fully rounded, never over half the height
        if r != self._radius:
            self._radius = r
            self._restyle()

    def set_state(self, text: str, variant: str):
        self.setText(text)
        self.set_variant(variant)


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setStyleSheet(dt.LINEEDIT_QSS)


class KeyField(QWidget):
    """Labelled secret input with show/hide and a status indicator."""

    key_changed = pyqtSignal(str)

    def __init__(self, label: str, env_key: str, current_value: str = "",
                 parent=None, placeholder: str = "Paste your API key…"):
        super().__init__(parent)
        self.env_key = env_key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        if label:
            lbl = QLabel(label)
            lbl.setFont(dt.font(14, dt.QFont.Weight.Medium))
            top.addWidget(lbl)
        top.addStretch()
        self._status = StatusDot(dt.SUCCESS if current_value else dt.TEXT_DIM)
        top.addWidget(self._status)
        self._indicator = QLabel("Saved" if current_value else "Not set")
        self._indicator.setFont(dt.FONT_CAPTION)
        self._indicator.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        top.addWidget(self._indicator)
        lay.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._input = QLineEdit(current_value)
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet(dt.LINEEDIT_QSS)
        self._input.textChanged.connect(self.key_changed.emit)
        row.addWidget(self._input, 1)

        self._eye = IconButton(icon="eye", tooltip="Show / hide")
        self._eye.setStyleSheet(self._eye.styleSheet() +
                                f"QPushButton {{ border: 1px solid {dt.BORDER_CSS}; }}")
        self._eye.clicked.connect(self._toggle_echo)
        row.addWidget(self._eye)
        lay.addLayout(row)

    def _toggle_echo(self):
        hidden = self._input.echoMode() == QLineEdit.EchoMode.Password
        self._input.setEchoMode(QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)
        self._eye.setIcon(icons.icon("eye-off" if hidden else "eye", dt.TEXT_MUTED.name(), 18))

    def get_key(self) -> str:
        return self._input.text().strip()

    def set_status(self, ok: bool):
        self._status.set_color(dt.SUCCESS if ok else dt.ERROR)
        self._indicator.setText("Valid" if ok else "Invalid")
        self._indicator.setStyleSheet(f"color: {(dt.SUCCESS if ok else dt.ERROR).name()};")

    def clear_key(self):
        self._input.clear()
        self._status.set_color(dt.TEXT_DIM)
        self._indicator.setText("Not set")
        self._indicator.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")


# ═════════════════════════════════════════════════════════════════════════════
#  Rows, groups, headers
# ═════════════════════════════════════════════════════════════════════════════

class SettingRow(QWidget):
    """Title + description on the left, a switch on the right."""

    toggled = pyqtSignal(bool)

    def __init__(self, label: str, description: str = "", checked: bool = False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(3)
        title = QLabel(label)
        title.setFont(dt.font(14, dt.QFont.Weight.Medium))
        left.addWidget(title)
        if description:
            d = QLabel(description)
            d.setFont(dt.FONT_CAPTION)
            d.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            d.setWordWrap(True)
            left.addWidget(d)
        lay.addLayout(left, 1)
        self.switch = ToggleSwitch(checked)
        self.switch.toggled.connect(self.toggled.emit)
        lay.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignVCenter)


class SettingsGroup(Card):
    """A card of rows separated by hairlines."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent, padding=20)
        self._layout.setSpacing(0)
        if title:
            t = QLabel(title.upper())
            t.setFont(dt.FONT_SECTION)
            t.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; letter-spacing: 1px; padding-bottom: 6px;")
            self._layout.addWidget(t)
        self._count = 0

    def add_row(self, widget: QWidget):
        if self._count or self._layout.count():
            if self._layout.count() and not isinstance(self._layout.itemAt(self._layout.count() - 1).widget(), QLabel):
                self._layout.addWidget(Divider())
            elif self._count:
                self._layout.addWidget(Divider())
        self._layout.addWidget(widget)
        self._count += 1
        return widget

    def add_toggle(self, label: str, description: str = "", checked: bool = False) -> SettingRow:
        row = SettingRow(label, description, checked)
        self.add_row(row)
        return row


class SectionHeader(QWidget):
    """Section title with optional hint and right-aligned action widget."""

    def __init__(self, title: str, hint: str = "", action: QWidget | None = None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(title)
        t.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        col.addWidget(t)
        if hint:
            h = QLabel(hint)
            h.setFont(dt.FONT_CAPTION)
            h.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            h.setWordWrap(True)
            col.addWidget(h)
        lay.addLayout(col, 1)
        if action is not None:
            lay.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)


class Banner(QFrame):
    """Inline notice. kind: info | success | warning | error."""

    _KIND = {
        "info":    ("rgba(110,139,255,0.10)", "rgba(110,139,255,0.30)", "#8FA6FF", "info"),
        "success": ("rgba(61,214,140,0.09)", "rgba(61,214,140,0.28)", dt.SUCCESS.name(), "check-circle"),
        "warning": ("rgba(245,165,36,0.09)", "rgba(245,165,36,0.30)", dt.WARNING.name(), "alert"),
        "error":   ("rgba(245,97,106,0.09)", "rgba(245,97,106,0.30)", dt.ERROR.name(), "alert"),
    }

    def __init__(self, text: str, kind: str = "info", action: QWidget | None = None, parent=None):
        super().__init__(parent)
        bg, line, fg, icon_name = self._KIND.get(kind, self._KIND["info"])
        self.setObjectName("Banner")
        self.setStyleSheet(f"QFrame#Banner {{ background: {bg}; border: 1px solid {line}; "
                           f"border-radius: {dt.BUTTON_RADIUS + 2}px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(icons.pixmap(icon_name, fg, 18))
        ic.setFixedSize(18, 18)
        lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setFont(dt.font(13))
        self.label.setStyleSheet("color: #DDE0EA;")
        lay.addWidget(self.label, 1)
        if action is not None:
            lay.addWidget(action, 0, Qt.AlignmentFlag.AlignVCenter)


class Segmented(QFrame):
    """Pill-style tab switcher. Emits the selected index."""

    changed = pyqtSignal(int)

    def __init__(self, labels: list, parent=None):
        super().__init__(parent)
        self.setObjectName("Segmented")
        self.setStyleSheet(f"QFrame#Segmented {{ background: {dt.BG_INPUT.name()}; "
                           f"border: 1px solid {dt.BORDER_CSS}; border-radius: 12px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self._buttons: list = []
        for i, text in enumerate(labels):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(32)
            b.clicked.connect(lambda _c=False, idx=i: self.select(idx))
            lay.addWidget(b)
            self._buttons.append(b)
        lay.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self._index = -1
        self.select(0, emit=False)

    def select(self, index: int, emit: bool = True):
        index = max(0, min(index, len(self._buttons) - 1))
        for i, b in enumerate(self._buttons):
            on = i == index
            b.setChecked(on)
            b.setStyleSheet(f"""
                QPushButton {{ border: none; border-radius: 9px; padding: 0 16px; font-size: 13px;
                    font-weight: 600; color: {dt.TEXT_PRIMARY.name() if on else dt.TEXT_MUTED.name()};
                    background: {dt.BG_ELEVATED.name() if on else 'transparent'}; }}
                QPushButton:hover {{ color: {dt.TEXT_PRIMARY.name()}; }}
            """)
        changed = index != self._index
        self._index = index
        if emit and changed:
            self.changed.emit(index)

    @property
    def index(self) -> int:
        return self._index


# ═════════════════════════════════════════════════════════════════════════════
#  Stat + progress cards
# ═════════════════════════════════════════════════════════════════════════════

class StatCard(Card):
    """Compact tile: small label, strong value (and optional icon)."""

    def __init__(self, label: str, value: str = "—", parent=None, icon: str | None = None):
        super().__init__(parent, padding=18)
        self._layout.setSpacing(8)
        top = QHBoxLayout()
        top.setSpacing(8)
        if icon:
            ic = QLabel()
            ic.setPixmap(icons.pixmap(icon, dt.TEXT_DIM.name(), 16))
            ic.setFixedSize(16, 16)
            top.addWidget(ic)
        title = QLabel(label)
        title.setFont(dt.FONT_CAPTION)
        title.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        top.addWidget(title)
        top.addStretch()
        self._layout.addLayout(top)
        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(dt.font(17, dt.QFont.Weight.DemiBold))
        self._layout.addWidget(self.value_lbl)

    def set_value(self, text: str, color: QColor | None = None):
        self.value_lbl.setText(text)
        self.value_lbl.setStyleSheet(f"color: {(color or dt.TEXT_PRIMARY).name()};")


class ProgressCard(Card):
    """Card with an embedded progress bar (used by model downloads)."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        lbl = QLabel(label)
        lbl.setFont(dt.font(14, dt.QFont.Weight.Medium))
        self.add_widget(lbl)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: {dt.BG_INPUT.name()}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ border-radius: 3px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()}); }}
        """)
        self.add_widget(self._bar)
        self._status = QLabel("")
        self._status.setFont(dt.FONT_CAPTION)
        self._status.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self.add_widget(self._status)

    def set_progress(self, pct: int, status: str = ""):
        self._bar.setVisible(True)
        self._bar.setValue(pct)
        if status:
            self._status.setText(status)

    def set_done(self, success: bool, message: str):
        self._bar.setVisible(False)
        self._status.setStyleSheet(f"color: {(dt.SUCCESS if success else dt.ERROR).name()};")
        self._status.setText(message)
