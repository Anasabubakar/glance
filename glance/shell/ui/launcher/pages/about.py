"""About — what Glance is, who made it, where to get help."""

from __future__ import annotations

import subprocess
import sys
import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from .. import design_tokens as dt
from ..page_base import BasePage
from ..widgets import Card, Divider, FlatButton, GradientButton


class AboutPage(BasePage):
    title = "About"
    icon = "info"
    subtitle = "Your intelligent cursor."

    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            import glance
            ver = glance.__version__
        except Exception:
            ver = "dev"

        hero = Card(padding=32)
        hero._layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        hero._layout.setSpacing(6)
        logo_pm = dt.load_pixmap("glance-flat.png", size=72)
        if not logo_pm.isNull():
            logo = QLabel()
            logo.setPixmap(logo_pm)
            logo.setFixedSize(72, 72)
            hero.add_widget(logo)
            hero._layout.setAlignment(logo, Qt.AlignmentFlag.AlignHCenter)
        for text, font, color in (("Glance", dt.font(26, dt.QFont.Weight.Bold), dt.TEXT_PRIMARY),
                                  ("Your AI companion for the desktop", dt.font(14), dt.TEXT_MUTED),
                                  (f"Version {ver}  ·  {self._commit()}", dt.FONT_CAPTION, dt.TEXT_DIM)):
            lbl = QLabel(text)
            lbl.setFont(font)
            lbl.setStyleSheet(f"color: {color.name()};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hero.add_widget(lbl)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.setSpacing(10)
        gh = GradientButton("GitHub", icon="external")
        gh.clicked.connect(lambda: webbrowser.open("https://github.com/Anasabubakar/glance"))
        bug = FlatButton("Report a problem")
        bug.clicked.connect(lambda: webbrowser.open("https://github.com/Anasabubakar/glance/issues"))
        row.addWidget(gh)
        row.addWidget(bug)
        hero.add_layout(row)
        self.body_layout.addWidget(hero)

        self.body_layout.addWidget(self.section_label("Credits"))
        credits = Card(padding=20)
        credits._layout.setSpacing(10)
        for k, v in (("Created by", "Anas Abubakar"),
                     ("Built on", "Clicky, Clicky for Windows and OpenClicky"),
                     ("License", "MIT")):
            r = QHBoxLayout()
            a = QLabel(k)
            a.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
            a.setFixedWidth(110)
            b = QLabel(v)
            r.addWidget(a)
            r.addWidget(b, 1)
            credits.add_layout(r)
        self.body_layout.addWidget(credits)
        self.body_layout.addStretch()

    @staticmethod
    def _commit() -> str:
        if getattr(sys, "frozen", False):
            return "release build"
        try:
            r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                               text=True, timeout=3)
            if r.returncode == 0:
                return f"build {r.stdout.strip()}"
        except Exception:
            pass
        return "development build"
