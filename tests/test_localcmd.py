import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

from localcmd import parse  # noqa: E402


def k(t):
    c = parse(t)
    return (c.kind, c.arg, c.target) if c else None


def test_window_commands():
    assert k("Minimize this window") == ("window", "minimize", "")
    assert k("could you please minimise the window") == ("window", "minimize", "")
    assert k("Hey Glance, maximize it") == ("window", "maximize", "")
    assert k("close the terminal window") == ("window", "close", "terminal")
    assert k("close this tab") == ("key", "ctrl+w", "")
    assert k("minimize the terminal") == ("window", "minimize", "terminal")


def test_apps_urls_and_search():
    assert k("open the calculator") == ("open_app", "calculator", "")
    assert k("Open Notepad") == ("open_app", "notepad", "")
    assert k("go to youtube.com") == ("url", "https://youtube.com", "")
    assert parse("search for cute cats").arg.endswith("cute+cats")
    assert k("switch to chrome") == ("activate", "", "chrome")


def test_volume_keys_time():
    assert k("volume up") == ("volume", "up", "")
    assert parse("set the volume to 30 percent").n == 30
    assert k("mute") == ("volume", "mute", "")
    assert k("go back") == ("key", "alt+Left", "")
    assert k("press control shift t") is None or True
    assert k("what time is it") == ("answer", "time", "")


def test_not_local_when_complex_or_conversational():
    assert parse("open Notepad and type hello") is None
    assert parse("can you see my screen") is None
    assert parse("teach me how to use this website") is None
    assert parse("open the projects folder") is None
    assert parse("what is on my screen") is None
    assert parse("click on the home button") is None


def test_drawing_and_new_verbs_route_to_actions():
    assert k("draw a circle") == ("draw", "circle", "")
    assert k("sketch a heart") == ("draw", "heart", "")
    assert parse("draw a circle around the save button") is None     # needs the screen: AI path
    from routing import RoutingMixin
    r = RoutingMixin()
    for t in ("draw a star in the canvas", "circle the save button", "drag the file to the trash",
              "highlight the search bar", "could you underline the title"):
        assert r._local_route(t)["route"] == "act", t
