"""
window.py — Premium LauncherWindow with fade-in, window icon, keyboard navigation.
"""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon

from . import design_tokens as dt
from .sidebar import Sidebar


class LauncherWindow(QMainWindow):
    """The main dashboard — sidebar navigation + stacked content pages."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Glance — Dashboard")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)
        self._companion_running = False
        self._fade_anim = None
        self._enter_anim = None

        # ── Window icon ──────────────────────────────────────────────────
        icon = dt.load_icon("glance-flat.png")
        if not icon.isNull():
            self.setWindowIcon(icon)

        # ── Base stylesheet ──────────────────────────────────────────────
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {dt.BG_DEEP.name()};
            }}
            QWidget {{
                background: transparent;
                color: {dt.TEXT_PRIMARY.name()};
            }}
            QLabel {{
                background: transparent;
            }}
            *:focus {{
                outline: none;
            }}
            QPushButton:focus {{
                border: 1px solid {dt.BRAND_INDIGO.name()};
            }}
        """)

        # ── Central widget ───────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_selected.connect(self._navigate)
        layout.addWidget(self._sidebar)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {dt.BG_DEEP.name()};")
        layout.addWidget(self._stack, 1)

        # ── Register pages ───────────────────────────────────────────────
        self._pages: dict[str, QWidget] = {}
        self._page_keys: list[str] = []
        self._register_pages()

        # ── Restore geometry ────────────────────────────────────────────
        settings = QSettings("Glance", "Launcher")
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)

        # ── Navigate to last page ────────────────────────────────────────
        last = os.environ.get("GLANCE_LAST_PAGE", "home").strip()
        if last not in self._pages:
            last = "home"
        self._navigate(last)

    def _register_pages(self):
        from .pages.home import HomePage
        from .pages.api_keys import APIKeysPage
        from .pages.providers import ProvidersPage
        from .pages.settings import SettingsPage
        from .pages.models import ModelsPage
        from .pages.ollama import OllamaPage
        from .pages.extensions import ExtensionsPage
        from .pages.workspace import WorkspacePage
        from .pages.updates import UpdatesPage
        from .pages.logs import LogsPage
        from .pages.diagnostics import DiagnosticsPage
        from .pages.cache import CachePage
        from .pages.memory import MemoryPage
        from .pages.downloads import DownloadsPage
        from .pages.security import SecurityPage
        from .pages.about import AboutPage
        from .pages.advanced import AdvancedPage

        pages = [
            ("home",        HomePage(self)),
            ("api_keys",    APIKeysPage(self)),
            ("providers",   ProvidersPage(self)),
            ("settings",    SettingsPage(self)),
            ("models",      ModelsPage(self)),
            ("ollama",      OllamaPage(self)),
            ("extensions",  ExtensionsPage(self)),
            ("workspace",   WorkspacePage(self)),
            ("updates",     UpdatesPage(self)),
            ("logs",        LogsPage(self)),
            ("diagnostics", DiagnosticsPage(self)),
            ("cache",       CachePage(self)),
            ("memory",      MemoryPage(self)),
            ("downloads",   DownloadsPage(self)),
            ("security",    SecurityPage(self)),
            ("about",       AboutPage(self)),
            ("advanced",    AdvancedPage(self)),
        ]
        for key, page in pages:
            self._pages[key] = page
            self._page_keys.append(key)
            self._stack.addWidget(page)

    def _navigate(self, key: str):
        page = self._pages.get(key)
        if not page:
            return

        # If already on this page, just re-activate
        if self._stack.currentWidget() is page:
            if hasattr(page, "on_activate"):
                page.on_activate()
            return

        # Fade-in transition
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        self._fade_anim = QPropertyAnimation(effect, b"opacity")
        self._fade_anim.setDuration(150)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(lambda: page.setGraphicsEffect(None))

        self._stack.setCurrentWidget(page)
        self._sidebar.set_active(key)
        self._fade_anim.start()

        if hasattr(page, "on_activate"):
            page.on_activate()

        # Persist last page
        try:
            from config import cfg
            cfg._persist_env("GLANCE_LAST_PAGE", key)
        except Exception:
            pass

    # ── Companion lifecycle ─────────────────────────────────────────────────

    def start_companion(self):
        """Launch the companion and hide the dashboard."""
        if self._companion_running:
            return
        self._companion_running = True

        home = self._pages.get("home")
        if home and hasattr(home, "set_companion_running"):
            home.set_companion_running(True)

        self.hide()

        import main as shell_main
        shell_main.main(launcher_window=self)

    def show_dashboard(self):
        """Reopen the launcher from the tray."""
        self.show()
        self.raise_()
        self.activateWindow()
        current = self._stack.currentWidget()
        if hasattr(current, "on_activate"):
            current.on_activate()

    def set_companion_running(self, running: bool):
        self._companion_running = running
        home = self._pages.get("home")
        if home and hasattr(home, "set_companion_running"):
            home.set_companion_running(running)

    # ── Window events ──────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        # Entry fade animation
        if self.windowOpacity() < 0.99:
            self._enter_anim = QPropertyAnimation(self, b"windowOpacity")
            self._enter_anim.setDuration(200)
            self._enter_anim.setStartValue(0.0)
            self._enter_anim.setEndValue(1.0)
            self._enter_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._enter_anim.start()

    def closeEvent(self, event):
        settings = QSettings("Glance", "Launcher")
        settings.setValue("geometry", self.saveGeometry())
        if self._companion_running:
            self.hide()
            event.ignore()
        else:
            event.accept()

    # ── Keyboard navigation ────────────────────────────────────────────────

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = mods == Qt.KeyboardModifier.ControlModifier

        if key == Qt.Key.Key_Escape:
            if self._companion_running:
                self.hide()
            else:
                self.close()
            return

        if ctrl:
            idx = self._page_keys.index(
                next((k for k, p in self._pages.items()
                      if p == self._stack.currentWidget()), "home")
            ) if self._page_keys else 0

            if key == Qt.Key.Key_BracketLeft and idx > 0:
                self._navigate(self._page_keys[idx - 1])
            elif key == Qt.Key.Key_BracketRight and idx < len(self._page_keys) - 1:
                self._navigate(self._page_keys[idx + 1])
            elif key == Qt.Key.Key_Home:
                self._navigate("home")
            elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
                num = key - Qt.Key.Key_1
                if num < len(self._page_keys):
                    self._navigate(self._page_keys[num])
            elif key == Qt.Key.Key_R:
                current = self._stack.currentWidget()
                if hasattr(current, "on_activate"):
                    current.on_activate()
            else:
                super().keyPressEvent(event)
                return
            return

        super().keyPressEvent(event)
