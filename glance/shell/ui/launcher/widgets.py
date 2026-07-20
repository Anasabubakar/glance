"""
widgets.py — Premium reusable widgets for the Glance Desktop Launcher.

Every visual component used across all 17 dashboard pages lives here.
Designed for consistency: same radii, same shadows, same hover language.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QGraphicsDropShadowEffect, QSizePolicy,
    QProgressBar,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QTimer, QRectF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QBrush,
    QFont, QPixmap,
)

from . import design_tokens as dt


# ═════════════════════════════════════════════════════════════════════════════
#  Loading Spinner
# ═════════════════════════════════════════════════════════════════════════════

class LoadingSpinner(QWidget):
    """Premium spinning arc — smooth, brand-colored, non-blocking."""

    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(20)      # 50 fps
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(dt.BRAND_INDIGO)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        p.drawArc(r, self._angle * 16, 280 * 16)
        p.end()


# ═════════════════════════════════════════════════════════════════════════════
#  Status Dot
# ═════════════════════════════════════════════════════════════════════════════

class StatusDot(QWidget):
    """Small filled circle — green / orange / red / grey / indigo."""

    def __init__(self, color: QColor = dt.TEXT_DIM, size: int = 8, parent=None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size, size)

    def set_color(self, color: QColor):
        self._color = color
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        hs = self._size // 2
        p.drawEllipse(1, 1, self._size - 2, self._size - 2)
        p.end()


# ═════════════════════════════════════════════════════════════════════════════
#  Card — the primary container
# ═════════════════════════════════════════════════════════════════════════════

class Card(QFrame):
    """Dark card with subtle border, rounded corners, and optional hover lift."""

    def __init__(self, parent=None, hoverable: bool = False):
        super().__init__(parent)
        self._hoverable = hoverable
        self._hovered = False

        self.setStyleSheet(f"""
            Card {{
                background: {dt.BG_CARD.name()};
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: {dt.CARD_RADIUS}px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(10)

        if self._hoverable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, _ev):
        if self._hoverable:
            self._hovered = True
            self._update_border()

    def leaveEvent(self, _ev):
        if self._hoverable:
            self._hovered = False
            self._update_border()

    def _update_border(self):
        c = f"1px solid {dt.BORDER_MEDIUM.name()}" if self._hovered else "1px solid rgba(255,255,255,0.06)"
        self.setStyleSheet(f"""
            Card {{
                background: {dt.BG_CARD.name()};
                border: {c};
                border-radius: {dt.CARD_RADIUS}px;
            }}
        """)

    def add_widget(self, w: QWidget):
        self._layout.addWidget(w)

    def add_layout(self, lay):
        self._layout.addLayout(lay)

    def clear_layout(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


# ═════════════════════════════════════════════════════════════════════════════
#  Toggle Switch (iOS-style)
# ═════════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._offset = 18.0 if checked else 2.0
        self.setFixedSize(dt.TOGGLE_TRACK_W, dt.TOGGLE_TRACK_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, on: bool, animate: bool = True):
        on = bool(on)
        if on == self._checked:
            return
        self._checked = on
        target = 18.0 if on else 2.0
        if animate:
            self._animate_to(target)
        else:
            self._offset = target
            self.update()

    def _animate_to(self, target: float):
        steps = 8
        step_size = (target - self._offset) / steps
        def _tick(remaining: int):
            if remaining <= 0:
                self._offset = target
                self.update()
                return
            self._offset += step_size
            self.update()
            QTimer.singleShot(12, lambda: _tick(remaining - 1))
        _tick(steps)

    def mousePressEvent(self, _ev):
        self._checked = not self._checked
        target = 18.0 if self._checked else 2.0
        self._animate_to(target)
        self.toggled.emit(self._checked)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        track = dt.BRAND_INDIGO if self._checked else QColor(60, 60, 80)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track))
        p.drawRoundedRect(0, 0, dt.TOGGLE_TRACK_W, dt.TOGGLE_TRACK_H,
                          dt.TOGGLE_TRACK_H / 2, dt.TOGGLE_TRACK_H / 2)

        # Thumb
        thumb_size = dt.TOGGLE_TRACK_H - 4
        thumb_r = int(self._offset)
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(thumb_r, 2, thumb_size, thumb_size)

        # Subtle shadow on thumb
        p.setBrush(QBrush(QColor(0, 0, 0, 20)))
        p.drawEllipse(thumb_r, 3, thumb_size, thumb_size)
        p.end()


# ═════════════════════════════════════════════════════════════════════════════
#  Key Field — API key input with mask/reveal and status
# ═════════════════════════════════════════════════════════════════════════════

class KeyField(QWidget):
    key_changed = pyqtSignal(str)

    def __init__(self, label: str, env_key: str, current_value: str = "",
                 parent=None):
        super().__init__(parent)
        self.env_key = env_key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        # Label row
        top = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(dt.FONT_BODY)
        lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        top.addWidget(lbl)
        top.addStretch()

        self._status = StatusDot(dt.SUCCESS if current_value else dt.TEXT_DIM)
        top.addWidget(self._status)

        indicator = QLabel("✓" if current_value else "")
        indicator.setFont(dt.FONT_CAPTION)
        indicator.setStyleSheet(f"color: {dt.SUCCESS.name()};" if current_value
                                else f"color: {dt.TEXT_DIM.name()};")
        self._indicator = indicator
        top.addWidget(indicator)

        lay.addLayout(top)

        # Input row
        row = QHBoxLayout()
        row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setPlaceholderText("Paste your API key…")
        self._input.setText(current_value or "")
        self._input.textChanged.connect(lambda: self.key_changed.emit(self.get_key()))
        self._input.setStyleSheet(dt.LINEEDIT_QSS + f"""
            QLineEdit {{
                font-family: {dt.FONT_MONO.family()};
                font-size: 12px;
            }}
        """)
        row.addWidget(self._input, 1)

        self._reveal_btn = QPushButton("Show")
        self._reveal_btn.setFixedWidth(52)
        self._reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reveal_btn.clicked.connect(self._toggle_reveal)
        _style_small_btn(self._reveal_btn)
        row.addWidget(self._reveal_btn)

        lay.addLayout(row)

    def get_key(self) -> str:
        return self._input.text().strip()

    def set_status(self, ok: bool):
        self._status.set_color(dt.SUCCESS if ok else dt.ERROR)
        self._indicator.setText("✓" if ok else "✗")
        self._indicator.setStyleSheet(f"color: {dt.SUCCESS.name() if ok else dt.ERROR.name()};")

    def clear_key(self):
        self._input.clear()
        self._status.set_color(dt.TEXT_DIM)
        self._indicator.setText("")
        self._indicator.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")

    def _toggle_reveal(self):
        if self._input.echoMode() == QLineEdit.EchoMode.Password:
            self._input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._reveal_btn.setText("Hide")
        else:
            self._input.setEchoMode(QLineEdit.EchoMode.Password)
            self._reveal_btn.setText("Show")


# ═════════════════════════════════════════════════════════════════════════════
#  Buttons
# ═════════════════════════════════════════════════════════════════════════════

class GradientButton(QPushButton):
    """Primary action button — brand gradient background."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
        self._hover = False
        self.setStyleSheet("background: transparent; border: none;")

    def enterEvent(self, _ev):
        self._hover = True
        self.update()

    def leaveEvent(self, _ev):
        self._hover = False
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(0, 0, 0, 0)

        grad = QLinearGradient(
            float(r.left()), float(r.top()), float(r.right()), float(r.top())
        )
        grad.setColorAt(0, dt.BRAND_INDIGO)
        grad.setColorAt(1, dt.BRAND_VIOLET)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.setOpacity(1.0 if self.isEnabled() else 0.45)
        p.drawRoundedRect(r, dt.BUTTON_RADIUS, dt.BUTTON_RADIUS)

        if self._hover and self.isEnabled():
            p.setBrush(QBrush(QColor(255, 255, 255, 25)))
            p.drawRoundedRect(r, dt.BUTTON_RADIUS, dt.BUTTON_RADIUS)

        p.setOpacity(1.0)
        p.setPen(QPen(QColor(255, 255, 255)))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


class FlatButton(QPushButton):
    """Secondary button — dark elevated background, hover to brand."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, hover: bool):
        bg = f"rgba(100,107,242,0.15)" if hover else dt.BG_ELEVATED.name()
        border = dt.BRAND_INDIGO.name() if hover else "rgba(255,255,255,0.08)"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid {border};
                border-radius: {dt.BUTTON_RADIUS}px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: rgba(100,107,242,0.15);
                border-color: {dt.BRAND_INDIGO.name()};
            }}
            QPushButton:disabled {{
                color: {dt.TEXT_DIM.name()};
                background: {dt.BG_CARD.name()};
                border-color: transparent;
            }}
        """)

    def enterEvent(self, _ev):
        self._update_style(True)

    def leaveEvent(self, _ev):
        self._update_style(False)


class DangerButton(QPushButton):
    """Destructive action — red-tinted."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,70,70,0.1);
                color: {dt.ERROR.name()};
                border: 1px solid rgba(255,70,70,0.2);
                border-radius: {dt.BUTTON_RADIUS}px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: rgba(255,70,70,0.2);
                border-color: {dt.ERROR.name()};
            }}
            QPushButton:disabled {{
                color: {dt.TEXT_DIM.name()};
                background: rgba(255,70,70,0.04);
                border-color: transparent;
            }}
        """)


class IconButton(QPushButton):
    """Small icon button — transparent, brand on hover."""

    def __init__(self, text: str = "", tooltip: str = "", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {dt.TEXT_MUTED.name()};
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: rgba(100,107,242,0.15);
                color: {dt.TEXT_PRIMARY.name()};
            }}
        """)


# ═════════════════════════════════════════════════════════════════════════════
#  Pill Badge
# ═════════════════════════════════════════════════════════════════════════════

class PillBadge(QLabel):
    """Small coloured pill — status, tag, or category label."""

    Variants = {
        "default": ("rgba(255,255,255,0.04)", "rgba(255,255,255,0.08)", dt.TEXT_MUTED),
        "indigo":  ("rgba(100,107,242,0.1)",  "rgba(100,107,242,0.2)",  dt.BRAND_INDIGO),
        "green":   ("rgba(74,222,128,0.1)",   "rgba(74,222,128,0.2)",   dt.SUCCESS),
        "orange":  ("rgba(251,146,60,0.1)",   "rgba(251,146,60,0.2)",   dt.WARNING),
        "red":     ("rgba(255,70,70,0.1)",    "rgba(255,70,70,0.2)",    dt.ERROR),
        "violet":  ("rgba(140,122,250,0.1)",  "rgba(140,122,250,0.2)",  dt.BRAND_VIOLET),
    }

    def __init__(self, text: str, variant: str = "default", parent=None):
        super().__init__(text, parent)
        bg, border, fg = self.Variants.get(variant, self.Variants["default"])
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg.name()};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
        """)


# ═════════════════════════════════════════════════════════════════════════════
#  Search Field
# ═════════════════════════════════════════════════════════════════════════════

class SearchField(QLineEdit):
    """Styled search input with placeholder."""

    def __init__(self, placeholder: str = "Search…", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet(dt.LINEEDIT_QSS)
        self.setClearButtonEnabled(True)


# ═════════════════════════════════════════════════════════════════════════════
#  Setting Row — label + toggle
# ═════════════════════════════════════════════════════════════════════════════

class SettingRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, description: str = "",
                 checked: bool = False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        left = QVBoxLayout()
        left.setSpacing(2)

        lbl = QLabel(label)
        lbl.setFont(dt.FONT_BODY)
        lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        left.addWidget(lbl)

        if description:
            desc = QLabel(description)
            desc.setFont(dt.FONT_CAPTION)
            desc.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
            desc.setWordWrap(True)
            left.addWidget(desc)

        lay.addLayout(left, 1)
        self.switch = ToggleSwitch(checked)
        self.switch.toggled.connect(self.toggled.emit)
        lay.addWidget(self.switch)


# ═════════════════════════════════════════════════════════════════════════════
#  Stat Card — for the home page dashboard
# ═════════════════════════════════════════════════════════════════════════════

class StatCard(Card):
    """Compact card showing a label + value, used for provider status."""

    def __init__(self, label: str, value: str = "—", parent=None):
        super().__init__(parent)
        title = QLabel(label)
        title.setFont(dt.FONT_CAPTION)
        title.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self.add_widget(title)

        self.value_lbl = QLabel(value)
        self.value_lbl.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
        self.value_lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        self.add_widget(self.value_lbl)

    def set_value(self, text: str, color: QColor | None = None):
        self.value_lbl.setText(text)
        if color:
            self.value_lbl.setStyleSheet(f"color: {color.name()};")
        else:
            self.value_lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")


# ═════════════════════════════════════════════════════════════════════════════
#  Progress Card — used by Ollama pull
# ═════════════════════════════════════════════════════════════════════════════

class ProgressCard(Card):
    """Card with embedded progress bar."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        lbl = QLabel(label)
        lbl.setFont(dt.FONT_BODY)
        lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        self.add_widget(lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setVisible(False)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: {dt.BG_ELEVATED.name()};
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                font-size: 9px;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {dt.BRAND_INDIGO.name()}, stop:1 {dt.BRAND_VIOLET.name()});
                border-radius: 4px;
            }}
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
        color = dt.SUCCESS if success else dt.ERROR
        self._status.setStyleSheet(f"color: {color.name()};")
        self._status.setText(message)


# ═════════════════════════════════════════════════════════════════════════════
#  Internal helpers
# ═════════════════════════════════════════════════════════════════════════════

def _style_small_btn(btn: QPushButton):
    """Apply the compact secondary-button style used inside KeyField."""
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {dt.BG_ELEVATED.name()};
            color: {dt.TEXT_MUTED.name()};
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: {dt.INPUT_RADIUS}px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background: rgba(100,107,242,0.15);
            color: {dt.TEXT_PRIMARY.name()};
        }}
    """)
