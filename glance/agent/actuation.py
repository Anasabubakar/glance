"""
actuation.py — the OS action executor (Phase 2 scaffold).

Turns the agent's chosen actions ("click here", "type this") into real OS
input. This is the layer that makes Glance *act* rather than just point.

It deliberately mirrors the action vocabulary of Claude's Computer Use tool
(left_click / type / key / scroll / screenshot / …) so the agent loop in
``computer_loop.py`` can hand actions straight through after the permission
gate clears them.

Coordinate contract: coordinates are LOGICAL screen pixels, the same space
the hybrid pointer produces and the same the cursor overlay flies to.

Implementation: pynput (cross-platform). Kept abstract so the agent loop
and the trust tests don't depend on a real desktop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Actuator(ABC):
    """Executes a single validated action. Implementations touch the real OS;
    tests use a recording fake."""

    @abstractmethod
    def left_click(self, x: int, y: int) -> None: ...

    @abstractmethod
    def double_click(self, x: int, y: int) -> None: ...

    @abstractmethod
    def right_click(self, x: int, y: int) -> None: ...

    @abstractmethod
    def move(self, x: int, y: int) -> None: ...

    @abstractmethod
    def scroll(self, x: int, y: int, dy: int) -> None: ...

    @abstractmethod
    def type_text(self, text: str) -> None: ...

    @abstractmethod
    def key(self, combo: str) -> None: ...      # e.g. "ctrl+a", "enter"


    # Optional gestures. The GNOME actuator implements them all; the others use pynput.
    def triple_click(self, x: int, y: int) -> None:
        self.double_click(x, y)

    def middle_click(self, x: int, y: int) -> None:
        raise NotImplementedError

    def click_with(self, x: int, y: int, mods: str, button: int = 1, count: int = 1) -> None:
        self.left_click(x, y)

    def drag(self, x1: int, y1: int, x2: int, y2: int, ms: int = 700) -> None:
        raise NotImplementedError

    def draw(self, strokes: list, ms_per_stroke: int = 900) -> None:
        raise NotImplementedError


class RecordingActuator(Actuator):
    """Test/dry-run actuator — records calls instead of touching the OS.

    Lets the agent loop and the trust gate be exercised headlessly (and on
    camera as a 'preview' mode) with zero risk to the machine.
    """

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def left_click(self, x, y):   self.calls.append(("left_click", x, y))
    def double_click(self, x, y): self.calls.append(("double_click", x, y))
    def right_click(self, x, y):  self.calls.append(("right_click", x, y))
    def move(self, x, y):         self.calls.append(("move", x, y))
    def scroll(self, x, y, dy):   self.calls.append(("scroll", x, y, dy))
    def type_text(self, text):    self.calls.append(("type_text", text))
    def key(self, combo):         self.calls.append(("key", combo))
    def triple_click(self, x, y): self.calls.append(("triple_click", x, y))
    def middle_click(self, x, y): self.calls.append(("middle_click", x, y))
    def click_with(self, x, y, mods, button=1, count=1): self.calls.append(("click_with", x, y, mods))
    def drag(self, x1, y1, x2, y2, ms=700): self.calls.append(("drag", x1, y1, x2, y2))
    def draw(self, strokes, ms_per_stroke=900): self.calls.append(("draw", len(strokes)))


class WindowsActuator(Actuator):
    """Real backend via pynput. pynput is cross-platform (Windows/Linux/macOS)
    so this actuator works on all platforms despite the name. Coordinates are
    PHYSICAL screen pixels. pynput is imported lazily so importing this module
    (e.g. for RecordingActuator in tests) never requires it."""

    def __init__(self):
        from pynput.mouse import Controller as _Mouse, Button as _Button
        from pynput.keyboard import Controller as _Keyboard
        self._mouse = _Mouse()
        self._Button = _Button
        self._kbd = _Keyboard()

    def left_click(self, x, y):
        self._mouse.position = (int(x), int(y))
        self._mouse.click(self._Button.left, 1)

    def double_click(self, x, y):
        self._mouse.position = (int(x), int(y))
        self._mouse.click(self._Button.left, 2)

    def right_click(self, x, y):
        self._mouse.position = (int(x), int(y))
        self._mouse.click(self._Button.right, 1)

    def move(self, x, y):
        self._mouse.position = (int(x), int(y))

    def scroll(self, x, y, dy):
        self._mouse.position = (int(x), int(y))
        self._mouse.scroll(0, dy)

    def type_text(self, text):
        self._kbd.type(text)

    def triple_click(self, x, y):
        self._mouse.position = (int(x), int(y))
        self._mouse.click(self._Button.left, 3)

    def middle_click(self, x, y):
        self._mouse.position = (int(x), int(y))
        self._mouse.click(self._Button.middle, 1)

    def click_with(self, x, y, mods, button=1, count=1):
        from pynput.keyboard import Key
        names = {"ctrl": Key.ctrl, "control": Key.ctrl, "alt": Key.alt, "shift": Key.shift,
                 "super": Key.cmd, "win": Key.cmd, "cmd": Key.cmd}
        held = [names[m] for m in str(mods).lower().replace(",", "+").split("+") if m.strip() in names]
        btn = {1: self._Button.left, 2: self._Button.middle, 3: self._Button.right}.get(int(button), self._Button.left)
        for m in held:
            self._kbd.press(m)
        try:
            self._mouse.position = (int(x), int(y))
            self._mouse.click(btn, int(count))
        finally:
            for m in reversed(held):
                self._kbd.release(m)

    def _stroke(self, pts, ms):
        import time as _t
        self._mouse.position = (int(pts[0][0]), int(pts[0][1]))
        _t.sleep(0.05)
        self._mouse.press(self._Button.left)
        try:
            step = max(0.004, ms / 1000.0 / max(1, len(pts)))
            for x, y in pts[1:]:
                self._mouse.position = (int(x), int(y))
                _t.sleep(step)
        finally:
            self._mouse.release(self._Button.left)

    def drag(self, x1, y1, x2, y2, ms=700):
        n = max(2, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 10))
        pts = [(x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n) for i in range(n + 1)]
        self._stroke(pts, ms)

    def draw(self, strokes, ms_per_stroke=900):
        for st in strokes:
            if len(st) >= 2:
                self._stroke(st, ms_per_stroke)

    def key(self, combo):
        """Press a key or chord: 'enter', 'cmd' (the Windows key), 'ctrl+c',
        'cmd+space', 'alt+tab'. Modifiers are held while the final key is tapped."""
        from pynput.keyboard import Key
        mods = {"ctrl": Key.ctrl, "control": Key.ctrl, "alt": Key.alt,
                "shift": Key.shift, "cmd": Key.cmd, "win": Key.cmd,
                "super": Key.cmd, "meta": Key.cmd}
        named = {"enter": Key.enter, "return": Key.enter, "tab": Key.tab,
                 "esc": Key.esc, "escape": Key.esc, "space": Key.space,
                 "backspace": Key.backspace, "delete": Key.delete, "del": Key.delete,
                 "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
                 "home": Key.home, "end": Key.end, "pageup": Key.page_up,
                 "pagedown": Key.page_down, "cmd": Key.cmd, "win": Key.cmd,
                 "super": Key.cmd}
        parts = [p.strip().lower() for p in str(combo or "").split("+") if p.strip()]
        if not parts:
            return
        held = [mods[p] for p in parts[:-1] if p in mods]
        last = parts[-1]
        key = named.get(last, last if len(last) == 1 else None)
        if key is None:
            return
        for m in held:
            self._kbd.press(m)
        try:
            self._kbd.press(key)
            self._kbd.release(key)
        finally:
            for m in reversed(held):
                self._kbd.release(m)


LinuxActuator = WindowsActuator
