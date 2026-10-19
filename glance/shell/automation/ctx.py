"""
ctx.py — everything an automation handler may touch, behind one object, so handlers are
plain functions that are easy to unit test (see FakeCtx).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


class Ctx:
    """The real thing: talks to the system, the GNOME extension and the companion."""

    def __init__(self, manager=None):
        self.m = manager
        self.home = Path.home()
        self.linux = sys.platform.startswith("linux")

    # ── running things ───────────────────────────────────────────────────
    def run(self, args: list, timeout: float = 6.0):
        """(returncode, stdout) of a command; never raises."""
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            return 127, str(e)

    def spawn(self, args: list) -> bool:
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return True
        except OSError:
            return False

    def have(self, exe: str) -> bool:
        from shutil import which
        return which(exe) is not None

    # ── showing what is happening ────────────────────────────────────────
    def caption(self, text: str, hold: float = 0.6):
        if self.m:
            self.m._caption(text, hold=hold)

    def fly(self, x: float, y: float, label: str = "", hold: float = 0.9):
        if self.m:
            self.m.sig_point_at.emit(float(x), float(y), label)
            time.sleep(hold)

    def release(self):
        if self.m:
            self.m.sig_point_release.emit()

    # ── apps, pages, input ───────────────────────────────────────────────
    def launch(self, name: str) -> bool:
        return bool(self.m and self.m._launch_app(name))

    def open_url(self, url: str):
        if self.m:
            self.m._open_url(url)

    def actuator(self):
        return self.m._get_actuator() if self.m else None

    def key(self, combo: str):
        a = self.actuator()
        if a:
            self.m._exec_action(a, "key", None, None, combo)

    def type_text(self, text: str):
        a = self.actuator()
        if a:
            self.m._exec_action(a, "type", None, None, text)

    def scroll(self, dy: int):
        a = self.actuator()
        if not a:
            return
        cx, cy = 640, 400
        if self.linux:
            from screen import gnome_bridge as gb
            st = gb.state() or {}
            cx = int(st.get("stage", {}).get("w", 1280) / 2)
            cy = int(st.get("stage", {}).get("h", 720) / 2)
        a.scroll(cx, cy, dy)

    # ── windows, clipboard ───────────────────────────────────────────────
    def bridge_ok(self) -> bool:
        if not self.linux:
            return False
        from screen import gnome_bridge as gb
        return gb.available() and gb.supports_windows()

    def windows(self) -> list:
        if not self.bridge_ok():
            return []
        from screen import gnome_bridge as gb
        return [w for w in gb.windows() if not w.get("glance")]

    def window_action(self, which: str, action: str):
        from screen import gnome_bridge as gb
        return gb.window_action(which, action)

    def clipboard_get(self, kind: str = "clipboard") -> str:
        if self.linux:
            from screen import gnome_bridge as gb
            if gb.available():
                return gb.get_clipboard(kind)
        return ""

    def clipboard_set(self, text: str):
        if self.linux:
            from screen import gnome_bridge as gb
            gb.set_clipboard(text)

    # ── asking and telling ───────────────────────────────────────────────
    def confirm(self, what: str) -> bool:
        return bool(self.m and self.m.confirm_blocking(what))

    def notify(self, msg: str):
        self.spawn(["notify-send", "Glance", msg])


class FakeCtx(Ctx):
    """For tests: records what would happen and returns programmable answers."""

    def __init__(self, files=None, wins=None, outputs=None):
        super().__init__(None)
        self.calls: list = []
        self.wins = wins or []
        self.outputs = outputs or {}
        self.clip = ""
        self.confirm_answer = True
        self.home = Path(files) if files else Path("/nonexistent-home")
        self.linux = True

    def run(self, args, timeout=6.0):
        self.calls.append(("run", list(args)))
        return 0, self.outputs.get(" ".join(args), "")

    def spawn(self, args):
        self.calls.append(("spawn", list(args)))
        return True

    def have(self, exe):
        return True

    def caption(self, text, hold=0.6):
        self.calls.append(("caption", text))

    def fly(self, x, y, label="", hold=0.9):
        self.calls.append(("fly", label))

    def release(self):
        pass

    def launch(self, name):
        self.calls.append(("launch", name))
        return name not in ("nonexistent app",)

    def open_url(self, url):
        self.calls.append(("url", url))

    def key(self, combo):
        self.calls.append(("key", combo))

    def type_text(self, text):
        self.calls.append(("type", text))

    def scroll(self, dy):
        self.calls.append(("scroll", dy))

    def bridge_ok(self):
        return True

    def windows(self):
        return list(self.wins)

    def window_action(self, which, action):
        self.calls.append(("window", which, action))
        return {"ok": True}

    def clipboard_get(self, kind="clipboard"):
        return self.clip

    def clipboard_set(self, text):
        self.clip = text
        self.calls.append(("clip", text))

    def confirm(self, what):
        self.calls.append(("confirm", what))
        return self.confirm_answer

    def notify(self, msg):
        self.calls.append(("notify", msg))
