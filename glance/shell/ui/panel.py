import asyncio
from enum import Enum, auto
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QComboBox, QFrame, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor

from ui.launcher import design_tokens as dt
from ui.launcher import icons
from ui.launcher.widgets import GradientButton, IconButton, PillBadge, StatusDot
from config import cfg

PANEL_WIDTH, PANEL_HEIGHT, PANEL_RADIUS = 384, 580, 22
ANIM_FAST_MS = 150


class AppState(Enum):
    IDLE      = auto()
    LISTENING = auto()
    THINKING  = auto()
    SPEAKING  = auto()


STATE_LABELS = {
    AppState.IDLE:      "Ready",
    AppState.LISTENING: "Listening",
    AppState.THINKING:  "Thinking",
    AppState.SPEAKING:  "Speaking",
}

STATE_COLORS = {
    AppState.IDLE:      QColor(107, 112, 131),
    AppState.LISTENING: QColor(61, 214, 140),
    AppState.THINKING:  QColor(110, 139, 255),
    AppState.SPEAKING:  QColor(245, 165, 36),
}


def _hotkey_text() -> str:
    parts = [p.strip().capitalize() if len(p.strip()) > 1 else p.strip().upper()
             for p in str(getattr(cfg, "hotkey", "ctrl+alt+m")).split("+")]
    return " + ".join(parts)


def _state_hint(state: "AppState") -> str:
    return {
        AppState.IDLE: f"Say “Glance” or hold {_hotkey_text()}",
        AppState.LISTENING: "Go ahead, I'm listening",
        AppState.THINKING: "Working on it…",
        AppState.SPEAKING: "Tap Esc to stop",
    }[state]


class WaveformWidget(QWidget):
    """Animated waveform bars shown while listening."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._levels = [0.0] * 20
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._decay)

    def set_level(self, rms: float):
        import random
        peak = min(1.0, rms * 3)
        self._levels = [min(1.0, peak * (0.4 + random.random() * 0.6)) for _ in self._levels]
        self.update()

    def _decay(self):
        self._levels = [max(0.0, v * 0.85) for v in self._levels]
        self.update()

    def start(self):
        self._timer.start(50)

    def stop(self):
        self._timer.stop()
        self._levels = [0.0] * 20
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = max(3, (w - 4 * len(self._levels)) // len(self._levels))
        spacing = (w - bar_w * len(self._levels)) // (len(self._levels) + 1)
        for i, level in enumerate(self._levels):
            x = spacing + i * (bar_w + spacing)
            bar_h = max(4, int(level * (h - 8)))
            y = (h - bar_h) // 2
            alpha = max(80, int(level * 255))
            color = QColor(91, 124, 255, alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(x, y, bar_w, bar_h, bar_w // 2, bar_w // 2)
        painter.end()


PROVIDER_LABELS = {
    "claude":  "Claude",
    "openai":  "GPT-4o",
    "gemini":  "Gemini",
    "copilot": "Copilot",
    "ollama":  f"Ollama ({cfg.ollama_model})",
    "custom":  "Custom (BYOK)",
    "cloud":   "Glance Cloud",
}

# Provider model lists are fetched live from each vendor's /models endpoint
# (see ai/model_registry.py for Claude/OpenAI/Gemini and
# ai/github_copilot_provider.py for Copilot). The hardcoded lists below are
# only used as offline fallbacks when no cache exists yet.


def _copilot_model_choices() -> list[tuple[str, str]]:
    """Returns [(model_id, display_label), ...] for the dropdown.
    Free models first, then ascending multiplier. Display shows '(free)' /
    '(1×)' so the user always knows what burns premium quota."""
    try:
        from ai.github_copilot_provider import (
            cached_models, sorted_model_ids, model_label,
        )
    except Exception:
        return [("gpt-4o-mini", "gpt-4o-mini  (free)")]
    out = []
    for mid in sorted_model_ids():
        out.append((mid, model_label(mid)))
    if not out:
        out.append(("gpt-4o-mini", "gpt-4o-mini  (free)"))
    return out


class ProviderBadge(PillBadge):
    """Small pill showing the active provider."""

    def __init__(self, provider: str, parent=None):
        super().__init__("", "accent", parent)
        self.set_provider(provider)

    def set_provider(self, provider: str):
        self.setText(PROVIDER_LABELS.get(provider, provider))


class CompanionPanel(QWidget):
    """Floating companion control panel — equivalent to CompanionPanelView.swift."""

    on_push_to_talk_pressed  = pyqtSignal()
    on_push_to_talk_released = pyqtSignal()
    on_model_changed         = pyqtSignal(str)
    on_document_dropped      = pyqtSignal(str)
    _sig_copilot_code        = pyqtSignal(str, str)   # (user_code, verification_uri)
    _sig_copilot_error       = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._state = AppState.IDLE
        self._response_text = ""
        self._setup_window()
        self._build_ui()
        self._position_bottom_right()
        # Wire internal thread-safe signals → main-thread slots
        self._sig_copilot_code.connect(self._on_copilot_code)
        self._sig_copilot_error.connect(self._on_copilot_error)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(PANEL_WIDTH, PANEL_HEIGHT)
        self.setObjectName("panel")
        # Fonts / label / scrollbar / combo rules from the design system; the panel
        # background itself is painted in paintEvent.
        self.setStyleSheet(dt.APP_QSS + dt.arrow_qss())
        self.setAcceptDrops(True)   # drag-drop PDFs / DOCX / TXT

    # ── Drag-drop handlers ───────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.on_document_dropped.emit(path)
        event.acceptProposedAction()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # ── Header ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(10)
        mark = QLabel()
        pm = dt.load_pixmap("glance-flat.png", size=30)
        if not pm.isNull():
            mark.setPixmap(pm)
        mark.setFixedSize(30, 30)
        header.addWidget(mark)
        title = QLabel("Glance")
        title.setFont(dt.font(17, dt.QFont.Weight.Bold))
        header.addWidget(title)
        header.addStretch()
        self._badge = ProviderBadge(cfg.llm_provider())
        header.addWidget(self._badge)
        self._min_btn = IconButton(icon="x", tooltip="Hide (reopen from the tray icon)")
        self._min_btn.setFixedSize(32, 32)
        self._min_btn.clicked.connect(self.hide)
        header.addWidget(self._min_btn)
        root.addLayout(header)

        # ── Status block ────────────────────────────────────────────────────
        status = QFrame()
        status.setObjectName("status_card")
        status.setStyleSheet(f"QFrame#status_card {{ background: {dt.BG_CARD.name()}; "
                             f"border: 1px solid {dt.BORDER_CSS}; border-radius: 16px; }}")
        sl = QVBoxLayout(status)
        sl.setContentsMargins(16, 14, 16, 14)
        sl.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(10)
        self._status_dot = StatusDot(STATE_COLORS[AppState.IDLE], 9)
        top.addWidget(self._status_dot)
        self._status_label = QLabel(STATE_LABELS[AppState.IDLE])
        self._status_label.setFont(dt.font(16, dt.QFont.Weight.DemiBold))
        top.addWidget(self._status_label)
        top.addStretch()
        sl.addLayout(top)
        self._hint_label = QLabel(_state_hint(AppState.IDLE))
        self._hint_label.setFont(dt.font(13))
        self._hint_label.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        self._hint_label.setWordWrap(True)
        sl.addWidget(self._hint_label)
        self._waveform = WaveformWidget()
        self._waveform.setVisible(False)
        sl.addWidget(self._waveform)
        root.addWidget(status)

        # ── Response ────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        # empty state
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("mic", dt.TEXT_DIM.name(), 30))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(ic)
        et = QLabel("Ask about anything on your screen")
        et.setFont(dt.font(14, dt.QFont.Weight.Medium))
        et.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(et)
        eh = QLabel("Glance will answer here and point at what it's talking about.")
        eh.setFont(dt.font(13))
        eh.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        eh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eh.setWordWrap(True)
        el.addWidget(eh)
        self._stack.addWidget(empty)
        # response
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }"
                             "QScrollArea > QWidget > QWidget { background: transparent; }")
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(2, 2, 6, 2)
        who = QLabel("GLANCE")
        who.setFont(dt.font(11, dt.QFont.Weight.DemiBold))
        who.setStyleSheet(f"color: {dt.TEXT_DIM.name()}; letter-spacing: 1px;")
        hl.addWidget(who)
        self._response_label = QLabel()
        self._response_label.setFont(dt.font(14))
        self._response_label.setWordWrap(True)
        self._response_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._response_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._response_label.setStyleSheet("color: #DDE0EA; line-height: 150%;")
        hl.addWidget(self._response_label)
        hl.addStretch()
        scroll.setWidget(holder)
        self._stack.addWidget(scroll)
        root.addWidget(self._stack, stretch=1)

        # ── Push-to-talk ────────────────────────────────────────────────────
        self._ptt_btn = GradientButton("Hold to talk", icon="mic")
        self._ptt_btn.setFixedHeight(48)
        self._ptt_btn.pressed.connect(self.on_push_to_talk_pressed.emit)
        self._ptt_btn.released.connect(self.on_push_to_talk_released.emit)
        root.addWidget(self._ptt_btn)

        # ── Footer: model ───────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(10)
        lbl = QLabel("Model")
        lbl.setFont(dt.FONT_CAPTION)
        lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        self._model_combo = QComboBox()
        self._model_combo.setMinimumHeight(34)
        self._populate_models()
        # Emit the model id (stored in userData), not the display label
        self._model_combo.currentIndexChanged.connect(
            lambda _idx: self.on_model_changed.emit(
                self._model_combo.currentData() or self._model_combo.currentText()
            )
        )
        footer.addWidget(lbl)
        footer.addWidget(self._model_combo, stretch=1)
        root.addLayout(footer)

    def _populate_models(self):
        self._set_models_for(cfg.llm_provider())

    def _set_models_for(self, provider: str):
        # Avoid firing on_model_changed while we rebuild
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        if provider == "copilot":
            for mid, label in _copilot_model_choices():
                self._model_combo.addItem(label, userData=mid)
        elif provider in ("claude", "openai", "gemini"):
            try:
                from ai.model_registry import cached_models
                if provider == "gemini":
                    # Google retires model names often; "auto" lets Glance pick a working one.
                    self._model_combo.addItem("Automatic (recommended)", userData="auto")
                for m in cached_models(provider):
                    label = m["id"]
                    if not m.get("vision"):
                        label += "  (no vision)"
                    self._model_combo.addItem(label, userData=m["id"])
            except Exception:
                self._model_combo.addItem("default", userData="default")
        elif provider == "custom":
            self._model_combo.addItem(cfg.custom_model or "model", userData=cfg.custom_model)
        elif provider == "cloud":
            self._model_combo.addItem("glance", userData="glance")
        else:   # ollama
            self._model_combo.addItem(cfg.ollama_model, userData=cfg.ollama_model)
        self._model_combo.blockSignals(False)
        # Fire once with the new default model id (NOT the display label) so
        # the manager picks it up — important when label != id.
        if self._model_combo.count():
            self.on_model_changed.emit(self._model_combo.currentData() or self._model_combo.currentText())

    def refresh_for_provider(self, provider: str):
        """Called from outside when the active provider is switched at runtime."""
        self._badge.set_provider(provider)
        self._set_models_for(provider)

    def _position_bottom_right(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.right() - PANEL_WIDTH - 24
        y = screen.bottom() - PANEL_HEIGHT - 60
        self.move(x, y)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: AppState):
        self._state = state
        self._status_dot.set_color(STATE_COLORS[state])
        self._status_label.setText(STATE_LABELS[state])
        self._hint_label.setText(_state_hint(state))
        self._hint_label.setVisible(bool(_state_hint(state)))
        self._waveform.setVisible(state == AppState.LISTENING)
        if state == AppState.LISTENING:
            self._waveform.start()
            self._ptt_btn.setText("Listening…  release to send")
        else:
            self._waveform.stop()
            self._ptt_btn.setText("Hold to talk")

    def _show_response(self, text: str):
        self._response_label.setText(text)
        self._stack.setCurrentIndex(1 if text.strip() else 0)

    def update_response(self, text: str):
        """Replace the response text."""
        self._response_text = text
        self._show_response(text)

    def append_response_chunk(self, chunk: str):
        self._response_text += chunk
        self._show_response(self._response_text)

    def set_audio_level(self, rms: float):
        self._waveform.set_level(rms)

    def clear_response(self):
        self._response_text = ""
        self._show_response("")

    def show_copilot_code(self, user_code: str, verification_uri: str):
        """Thread-safe: can be called from any thread. Emits a queued signal
        so the UI update always runs on the Qt main thread."""
        self._sig_copilot_code.emit(user_code, verification_uri)

    def show_copilot_error(self, error: str):
        """Thread-safe version of showing a Copilot login error."""
        self._sig_copilot_error.emit(error)

    # ── Private slots (always run on Qt main thread) ──────────────────────────

    def _on_copilot_code(self, user_code: str, verification_uri: str):
        self.show()   # bring panel to front
        self.raise_()
        self._response_text = (
            "── GitHub Copilot Sign-In ──\n\n"
            f"1.  Open:  {verification_uri}\n\n"
            f"2.  Enter code:\n\n"
            f"        {user_code}\n\n"
            "3.  Click Authorize in GitHub.\n\n"
            "Glance will sign in automatically once you authorize."
        )
        self._show_response(self._response_text)
        self._status_label.setText("Waiting for Copilot authorization…")

    def _on_copilot_error(self, error: str):
        self._response_text = f"Copilot login failed:\n\n{error}"
        self._show_response(self._response_text)

    # ── Mouse drag to reposition ──────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── Painting: rounded surface ─────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(15, 16, 21, 248)))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), PANEL_RADIUS, PANEL_RADIUS)
        painter.end()
