"""Reusable widgets for the launcher dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve,
    QTimer, QRectF,
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPen, QBrush, QConicalGradient

from . import design_tokens as dt


class LoadingSpinner(QWidget):
    """Small spinning arc indicator for async operations."""

    def __init__(self, size: int = 24, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._timer.start(25)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(dt.BRAND_INDIGO)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        p.drawArc(r, self._angle * 16, 270 * 16)
        p.end()


class StatusDot(QWidget):
    """8px circle — green, orange, red, or grey."""

    def __init__(self, color: QColor = dt.TEXT_DIM, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(8, 8)

    def set_color(self, color: QColor):
        self._color = color
        self.update()

    def set_status(self, color: QColor, tooltip: str = ""):
        self._color = color
        if tooltip:
            self.setToolTip(tooltip)
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(0, 0, 8, 8)
        p.end()


class Card(QFrame):
    """Dark card with subtle border, rounded corners, and soft shadow."""

    def __init__(self, parent=None):
        super().__init__(parent)
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

    def add_widget(self, w: QWidget):
        self._layout.addWidget(w)

    def add_layout(self, lay):
        self._layout.addLayout(lay)


class ToggleSwitch(QWidget):
    """iOS-style toggle switch."""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._offset = 18.0 if checked else 2.0
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, on: bool, animate=True):
        if on == self._checked:
            return
        self._checked = on
        target = 18.0 if on else 2.0
        if animate:
            self._animate(target)
        else:
            self._offset = target
            self.update()

    def _animate(self, target: float):
        step = 1.0 if target > self._offset else -1.0
        from PyQt6.QtCore import QTimer
        def _tick():
            self._offset += step * 2
            if (step > 0 and self._offset >= target) or (step < 0 and self._offset <= target):
                self._offset = target
                self.update()
                return
            self.update()
            QTimer.singleShot(10, _tick)
        _tick()

    def mousePressEvent(self, _ev):
        self._checked = not self._checked
        target = 18.0 if self._checked else 2.0
        self._animate(target)
        self.toggled.emit(self._checked)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Track
        track_color = dt.BRAND_INDIGO if self._checked else QColor(60, 60, 80)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(0, 0, 40, 22, 11, 11)
        # Thumb
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(int(self._offset), 2, 18, 18)
        p.end()


class KeyField(QWidget):
    """API key input with mask/reveal toggle and action buttons."""
    key_changed = pyqtSignal(str)

    def __init__(self, label: str, key_env: str, current_value: str = "", parent=None):
        super().__init__(parent)
        self.key_env = key_env
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        top = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(dt.FONT_BODY)
        lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        top.addWidget(lbl)
        top.addStretch()

        self._status = StatusDot(dt.SUCCESS if current_value else dt.TEXT_DIM)
        top.addWidget(self._status)
        lay.addLayout(top)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setEchoMode(QLineEdit.EchoMode.Password)
        self._input.setPlaceholderText("Paste your API key…")
        self._input.setText(current_value or "")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 8px 10px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {dt.BRAND_INDIGO.name()};
            }}
        """)
        row.addWidget(self._input, 1)

        self._reveal_btn = QPushButton("Show")
        self._reveal_btn.setFixedWidth(52)
        self._reveal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reveal_btn.clicked.connect(self._toggle_reveal)
        self._style_btn(self._reveal_btn)
        row.addWidget(self._reveal_btn)

        lay.addLayout(row)

    def get_key(self) -> str:
        return self._input.text().strip()

    def set_status(self, ok: bool):
        self._status.set_color(dt.SUCCESS if ok else dt.ERROR)

    def clear_key(self):
        self._input.clear()
        self._status.set_color(dt.TEXT_DIM)

    def _toggle_reveal(self):
        if self._input.echoMode() == QLineEdit.EchoMode.Password:
            self._input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._reveal_btn.setText("Hide")
        else:
            self._input.setEchoMode(QLineEdit.EchoMode.Password)
            self._reveal_btn.setText("Show")

    @staticmethod
    def _style_btn(btn: QPushButton):
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_MUTED.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: rgba(100,107,242,0.15);
                color: {dt.TEXT_PRIMARY.name()};
            }}
        """)


class GradientButton(QPushButton):
    """Primary action button with brand gradient."""

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
        p.setOpacity(1.0 if self.isEnabled() else 0.5)
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
    """Secondary flat button."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {dt.BG_ELEVATED.name()};
                color: {dt.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
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
            }}
        """)


class DangerButton(QPushButton):
    """Red-tinted destructive action button."""

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
            }}
        """)


class SettingRow(QWidget):
    """Label + optional description + toggle switch, in a single row."""
    toggled = pyqtSignal(bool)

    def __init__(self, label: str, description: str = "", checked: bool = False, parent=None):
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
