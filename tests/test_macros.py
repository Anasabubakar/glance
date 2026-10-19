import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import macros  # noqa: E402


def ev(t, kind, **d):
    return {"t": t, "kind": kind, "data": d}


def test_events_become_steps_and_letters_merge():
    steps = macros.to_steps([
        ev(0.1, "click", x=10, y=20, button=1),
        ev(0.5, "key", key="h", char="h", mods=0), ev(0.6, "key", key="i", char="i", mods=0),
        ev(0.7, "key", key="Shift_L", char="", mods=1),
        ev(0.9, "key", key="Return", char="", mods=0),
        ev(1.5, "key", key="s", char="s", mods=4),
    ])
    assert [s["do"] for s in steps] == ["click", "type", "key", "key"]
    assert steps[1]["text"] == "hi" and steps[2]["combo"] == "enter" and steps[3]["combo"] == "ctrl+s"


def test_save_load_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(macros, "DIR", tmp_path)
    macros.save("My Macro!", [ev(0, "click", x=5, y=6, button=1), ev(1, "key", key="a", char="a", mods=0)])
    assert macros.names() == ["My Macro!"]
    data = macros.load("my macro")
    calls = []

    class A:
        def left_click(self, x, y): calls.append(("click", x, y))
        def type_text(self, t): calls.append(("type", t))
        def key(self, c): calls.append(("key", c))

    monkeypatch.setattr(macros.time, "sleep", lambda s: None)
    n = macros.replay(data["steps"], A(), lambda x, y: (x * 2, y * 2))
    assert n == 2 and calls == [("click", 10, 12), ("type", "a")]
    assert "1 click" in macros.describe(data["steps"])
