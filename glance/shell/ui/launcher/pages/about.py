"""
About page — version, commit, credits, license, links.
"""

import sys
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
)
from PyQt6.QtCore import Qt

from ..page_base import BasePage
from ..widgets import Card, FlatButton
from .. import design_tokens as dt


class AboutPage(BasePage):
    title = "About"
    icon = "ℹ"
    subtitle = ""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Logo + Brand ───────────────────────────────────────────────
        brand_card = Card()
        brand_card._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Glance logo
        logo_pm = dt.load_pixmap("glance-flat.png", size=64)
        if not logo_pm.isNull():
            logo = QLabel()
            logo.setPixmap(logo_pm)
            logo.setFixedSize(64, 64)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            brand_card.add_widget(logo)

        name = QLabel("Glance")
        name.setFont(dt.font(28, dt.QFont.Weight.Bold))
        name.setStyleSheet(f"color: {dt.BRAND_INDIGO.name()};")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_card.add_widget(name)

        tagline = QLabel("Your AI companion for desktop")
        tagline.setFont(dt.FONT_BODY)
        tagline.setStyleSheet(f"color: {dt.TEXT_MUTED.name()};")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_card.add_widget(tagline)

        try:
            import glance
            ver = glance.__version__
        except Exception:
            ver = "dev"
        ver_lbl = QLabel(f"Version {ver}")
        ver_lbl.setFont(dt.font(14, dt.QFont.Weight.DemiBold))
        ver_lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_card.add_widget(ver_lbl)

        commit = self._get_commit()
        commit_lbl = QLabel(f"Build: {commit}")
        commit_lbl.setFont(dt.FONT_CAPTION)
        commit_lbl.setStyleSheet(f"color: {dt.TEXT_DIM.name()};")
        commit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_card.add_widget(commit_lbl)
        self.body_layout.addWidget(brand_card)

        # ── Credits ────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Credits"))
        credits_card = Card()
        for line in [
            "Created by Anas Abubakar",
            "Built on: Clicky, Clicky for Windows, OpenClicky",
            "License: MIT",
        ]:
            lbl = QLabel(line)
            lbl.setFont(dt.FONT_BODY)
            lbl.setStyleSheet(f"color: {dt.TEXT_PRIMARY.name()};")
            credits_card.add_widget(lbl)
        self.body_layout.addWidget(credits_card)

        # ── Links ──────────────────────────────────────────────────────
        self.body_layout.addWidget(self.section_label("Links"))
        links_card = Card()
        for label, url in [
            ("GitHub Repository", "https://github.com/Anasabubakar/Glance"),
            ("Report an Issue", "https://github.com/Anasabubakar/Glance/issues"),
        ]:
            btn = FlatButton(label)
            btn.clicked.connect(lambda _c=False, u=url: self._open_url(u))
            links_card.add_widget(btn)
        self.body_layout.addWidget(links_card)
        self.body_layout.addStretch()

    @staticmethod
    def _get_commit() -> str:
        if getattr(sys, "frozen", False):
            return "release build"
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _open_url(url: str):
        import webbrowser
        webbrowser.open(url)
