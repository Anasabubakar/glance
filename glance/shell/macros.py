"""
macros.py — record what you do once, replay it any time with no AI.

Workflow Capture records clicks, keys and scrolls (through the GNOME extension on
Wayland). A macro is that recording, saved under a name in ~/.glance/macros/. Replaying
sends the same input back through the actuator, flying the cursor to each click first so
you can watch it. Pure helpers here; the app drives them.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Callable

DIR = Path.home() / ".glance" / "macros"

_CTRL, _ALT, _SUPER = 4, 8, 1 << 26
_KEYMAP = {"Return": "enter", "KP_Enter": "enter", "BackSpace": "backspace", "Tab": "tab",
           "Escape": "esc", "Left": "left", "Right": "right", "Up": "up", "Down": "down",
           "Delete": "delete", "Home": "home", "End": "end", "Page_Up": "pageup",
           "Page_Down": "pagedown"}
_MODKEYS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Super_L", "Super_R",
            "Caps_Lock", "ISO_Level3_Shift", "Meta_L", "Meta_R"}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "macro"


def save(name: str, events: list) -> Path:
    steps = to_steps(events)
    DIR.mkdir(parents=True, exist_ok=True)
    p = DIR / f"{_slug(name)}.json"
    p.write_text(json.dumps({"name": name, "saved": time.time(), "steps": steps}, indent=1))
    return p


def load(name: str):
    p = DIR / f"{_slug(name)}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def names() -> list:
    try:
        return sorted(json.loads(p.read_text()).get("name", p.stem) for p in DIR.glob("*.json"))
    except (OSError, ValueError):
        return []


def to_steps(events: list) -> list:
    """Raw recorded events -> replayable steps: click / scroll / type / key with a delay (s)."""
    steps: list = []
    last_t = None
    for e in events:
        t = float(e.get("t", 0))
        gap = 0.25 if last_t is None else max(0.05, min(t - last_t, 3.0))
        last_t = t
        d = e.get("data", {})
        kind = e.get("kind")
        if kind == "click":
            steps.append({"do": "click", "x": d.get("x"), "y": d.get("y"),
                          "button": int(d.get("button", 1) or 1), "wait": gap})
        elif kind == "scroll":
            steps.append({"do": "scroll", "x": d.get("x"), "y": d.get("y"), "wait": gap})
        elif kind == "key":
            key = d.get("key", "")
            if key in _MODKEYS:
                continue
            mods = int(d.get("mods", 0) or 0)
            ch = d.get("char", "")
            if mods & (_CTRL | _ALT | _SUPER):
                combo = "+".join([m for m, bit in (("ctrl", _CTRL), ("alt", _ALT), ("super", _SUPER)) if mods & bit]
                                 + [(key or ch).lower() if len(key) > 1 or not key else key.lower()])
                steps.append({"do": "key", "combo": combo, "wait": gap})
            elif key in _KEYMAP:
                steps.append({"do": "key", "combo": _KEYMAP[key], "wait": gap})
            elif ch:
                if steps and steps[-1]["do"] == "type" and gap < 0.8:      # merge a run of letters
                    steps[-1]["text"] += ch
                else:
                    steps.append({"do": "type", "text": ch, "wait": gap})
    return steps


def describe(steps: list) -> str:
    n = {"click": 0, "type": 0, "key": 0, "scroll": 0}
    for s in steps:
        n[s["do"]] = n.get(s["do"], 0) + 1
    parts = [f"{v} {k}{'s' if v != 1 else ''}" for k, v in n.items() if v]
    return ", ".join(parts) or "nothing"


def replay(steps: list, actuator, to_physical: Callable, fly: Callable | None = None,
           stop: Callable[[], bool] = lambda: False, speed: float = 1.0) -> int:
    """Send the recorded input back. Returns how many steps ran. Coordinates in the file
    are logical screen pixels; `to_physical(x, y)` converts them for the actuator."""
    ran = 0
    for s in steps:
        if stop():
            break
        time.sleep(min(s.get("wait", 0.2) / max(speed, 0.1), 2.0))
        do = s["do"]
        if do in ("click", "scroll"):
            x, y = s["x"], s["y"]
            if fly:
                fly(x, y, "Replaying")
                time.sleep(0.5 / max(speed, 0.1))
            px, py = to_physical(x, y)
            if do == "scroll":
                actuator.scroll(px, py, -3)
            elif s.get("button") == 3:
                actuator.right_click(px, py)
            elif s.get("button") == 2:
                actuator.middle_click(px, py)
            else:
                actuator.left_click(px, py)
        elif do == "type":
            actuator.type_text(s["text"])
        elif do == "key":
            actuator.key(s["combo"])
        ran += 1
    return ran
