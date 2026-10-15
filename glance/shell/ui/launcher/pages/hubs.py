"""
hubs.py — tabbed pages that merge related, previously thin pages.

17 separate pages became 9: each hub hosts its sub-pages as tabs (built in
"embedded" mode, i.e. without their own header or scrolling).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QSizePolicy, QStackedWidget

from ..page_base import BasePage
from ..widgets import Segmented


class TabbedHub(BasePage):
    TABS: list = []          # [(label, PageClass)]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs = []
        labels = []
        for label, cls in self.TABS:
            labels.append(label)
            self._tabs.append(cls.embedded())
        self._seg = Segmented(labels)
        self.body_layout.addWidget(self._seg)
        self._stack = QStackedWidget()
        for page in self._tabs:
            self._stack.addWidget(page)
        self.body_layout.addWidget(self._stack)
        self._seg.changed.connect(self.set_tab)
        self.set_tab(0)

    def set_tab(self, index: int):
        index = max(0, min(index, len(self._tabs) - 1))
        if self._seg.index != index:
            self._seg.select(index, emit=False)
        self._stack.setCurrentIndex(index)
        # Only the visible tab may set the height (hidden tabs would leave blank space).
        for i, page in enumerate(self._tabs):
            page.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Preferred if i == index else QSizePolicy.Policy.Ignored)
        self._stack.updateGeometry()
        page = self._tabs[index]
        if hasattr(page, "on_activate"):
            page.on_activate()

    def on_activate(self):
        page = self._tabs[self._stack.currentIndex()]
        if hasattr(page, "on_activate"):
            page.on_activate()


def build_hubs():
    from .about import AboutPage
    from .advanced import AdvancedPage
    from .cache import CachePage
    from .diagnostics import DiagnosticsPage
    from .extensions import ExtensionsPage
    from .logs import LogsPage
    from .models import ModelsPage
    from .ollama import OllamaPage
    from .security import SecurityPage
    from .updates import UpdatesPage
    from .workspace import WorkspacePage

    class ModelsHub(TabbedHub):
        title, icon = "Models", "ai"
        subtitle = "Choose the model Glance uses, or run one on this computer."
        TABS = [("Cloud models", ModelsPage), ("On this computer", OllamaPage)]

    class IntegrationsHub(TabbedHub):
        title, icon = "Integrations", "grid"
        subtitle = "Skills Glance has learned and the services it can connect to."
        TABS = [("Skills", ExtensionsPage), ("Google Workspace", WorkspacePage)]

    class ActivityHub(TabbedHub):
        title, icon = "Activity", "activity"
        subtitle = "What Glance heard and did, and how healthy everything is."
        TABS = [("Log", LogsPage), ("Diagnostics", DiagnosticsPage)]

    class PrivacyHub(TabbedHub):
        title, icon = "Privacy & storage", "shield"
        subtitle = "Where your keys and data live, and tools to clean up."
        TABS = [("Credentials", SecurityPage), ("Cache", CachePage), ("Advanced", AdvancedPage)]

    class AboutHub(TabbedHub):
        title, icon = "About & updates", "info"
        subtitle = "Version, credits and new releases."
        TABS = [("About", AboutPage), ("Updates", UpdatesPage)]

    return {"models": ModelsHub, "extensions": IntegrationsHub, "logs": ActivityHub,
            "security": PrivacyHub, "about": AboutHub}
