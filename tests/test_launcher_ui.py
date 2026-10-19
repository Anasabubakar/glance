"""Smoke-test the desktop UI offscreen: every dashboard page builds and shows,
nav entries all resolve, the panel and wizard construct, settings tell the truth."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["GLANCE_NO_GNOME_BRIDGE"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

pytest.importorskip("PyQt6")
pytest.importorskip("PyQt6.QtSvg")

from PyQt6.QtWidgets import QApplication  # noqa: E402

_app = QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def window():
    from ui.launcher.window import LauncherWindow
    w = LauncherWindow()
    w.resize(1100, 740)
    w.show()
    _app.processEvents()
    yield w
    w.close()


def test_every_page_builds_and_activates(window):
    assert len(window._pages) == 10
    for key in window._pages:
        window._navigate(key)
        _app.processEvents()
        assert window._stack.currentWidget() is window._pages[key]


def test_every_nav_entry_and_alias_resolves(window):
    from ui.launcher.sidebar import NAV_PINNED, NAV_SECTIONS
    keys = [k for _s, items in NAV_SECTIONS for k, _l, _i in items] + [k for k, _l, _i in NAV_PINNED]
    for k in keys:
        assert k in window._pages, f"nav entry {k!r} has no page"
    for alias, (hub, tab) in window._ALIASES.items():
        assert hub in window._pages
        window._navigate(alias)
        if hasattr(window._pages[hub], "set_tab"):
            assert window._pages[hub]._seg.index == tab


def test_hub_tabs_switch(window):
    for key in ("models", "extensions", "logs", "security", "about"):
        hub = window._pages[key]
        for i in range(len(hub._tabs)):
            hub.set_tab(i)
            _app.processEvents()
            assert hub._stack.currentIndex() == i


def test_icons_all_render():
    from ui.launcher import icons
    for name in icons.names():
        pm = icons.pixmap(name, "#ffffff", 24)
        assert not pm.isNull()


def test_settings_show_real_defaults(window):
    import prefs
    page = window._pages["settings"]
    page.on_activate()
    for env, row in page._rows.items():
        assert row.switch.is_checked() == prefs.get(env)


def test_panel_states_and_response():
    from ui.panel import AppState, CompanionPanel
    p = CompanionPanel()
    for st in AppState:
        p.set_state(st)
    p.update_response("hello")
    assert p._stack.currentIndex() == 1
    p.clear_response()
    assert p._stack.currentIndex() == 0


def test_wizard_builds_with_free_option():
    from ui.setup_wizard import SetupWizard
    w = SetupWizard()
    assert w.free_btn.text() == "Start free"
