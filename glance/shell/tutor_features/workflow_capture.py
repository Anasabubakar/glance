"""
Workflow capture — record a sequence of clicks + keystrokes the user
performs, then let Glance explain or replay them.

Status: foundation laid. Hotkey + recording loop work. Replay layer is
intentionally a stub — playback of synthetic input is a security concern
and needs a careful UX (preview, confirm, undo) before it's safe to ship.

Use:
    capt = WorkflowCapture()
    capt.start()      # Ctrl+Alt+R → starts capture
    # ... user clicks around, types
    capt.stop()       # Ctrl+Alt+R again → stops, returns events list

Each event:  {"t": float, "kind": "click"|"key", "data": {...}}
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional


class WorkflowCapture:
    def __init__(self):
        self._events: list[dict] = []
        self._t0: float = 0.0
        self._is_running = False
        self._listener_kb = None
        self._listener_mouse = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def _start_gnome(self) -> bool:
        """GNOME/Wayland: the compositor sees every click and key (pynput can't), so the
        Glance extension reports them over D-Bus."""
        try:
            from screen import gnome_bridge
            if not gnome_bridge.available():
                return False
            from PyQt6.QtCore import QObject, pyqtSlot
            from PyQt6.QtDBus import QDBusConnection
            outer = self

            class _Rx(QObject):
                @pyqtSlot(str)
                def on_event(self, js):
                    import json
                    try:
                        e = json.loads(js)
                    except ValueError:
                        return
                    if not outer._is_running:
                        return
                    d = {k: v for k, v in e.items() if k not in ("kind", "t")}
                    if e.get("kind") == "key":
                        d["key"] = e.get("char") or e.get("key", "")
                    outer._events.append({"t": time.monotonic() - outer._t0,
                                          "kind": e.get("kind", "?"), "data": d})

            self._rx = _Rx()
            ok = QDBusConnection.sessionBus().connect(
                "app.glance.Overlay", "/app/glance/Overlay", "app.glance.Overlay",
                "InputEvent", self._rx.on_event)
            if not ok:
                return False
            gnome_bridge.set_recording(True)
            self._gnome = True
            return True
        except Exception:
            return False

    def start(self) -> bool:
        self._events = []
        self._t0 = time.monotonic()
        self._is_running = True
        self._gnome = False
        if self._start_gnome():
            return True
        try:
            from pynput import mouse, keyboard   # type: ignore
        except ImportError:
            self._is_running = False
            return False

        def on_click(x, y, button, pressed):
            if pressed and self._is_running:
                self._events.append({
                    "t": time.monotonic() - self._t0,
                    "kind": "click",
                    "data": {"x": x, "y": y, "button": str(button)},
                })

        def on_press(key):
            if self._is_running:
                self._events.append({
                    "t": time.monotonic() - self._t0,
                    "kind": "key",
                    "data": {"key": str(key)},
                })

        from pynput import mouse, keyboard
        self._listener_mouse = mouse.Listener(on_click=on_click)
        self._listener_kb    = keyboard.Listener(on_press=on_press)
        self._listener_mouse.start()
        self._listener_kb.start()
        return True

    def stop(self) -> list[dict]:
        if not self._is_running:
            return []
        self._is_running = False
        if getattr(self, "_gnome", False):
            try:
                from screen import gnome_bridge
                from PyQt6.QtDBus import QDBusConnection
                gnome_bridge.set_recording(False)
                QDBusConnection.sessionBus().disconnect(
                    "app.glance.Overlay", "/app/glance/Overlay", "app.glance.Overlay",
                    "InputEvent", self._rx.on_event)
            except Exception:
                pass
            self._gnome = False
        for li in (self._listener_mouse, self._listener_kb):
            try:
                if li:
                    li.stop()
            except Exception:
                pass
        return list(self._events)

    def summarise(self) -> str:
        """Plain-English summary the LLM can ingest."""
        if not self._events:
            return "(no actions recorded)"
        lines = []
        for e in self._events[:40]:
            t = e["t"]
            d = e["data"]
            win = f" in '{d['window']}'" if d.get("window") else ""
            if e["kind"] == "click":
                lines.append(f"  [{t:5.1f}s] click {d.get('button', '')} at ({d.get('x')}, {d.get('y')}){win}")
            elif e["kind"] == "scroll":
                lines.append(f"  [{t:5.1f}s] scroll at ({d.get('x')}, {d.get('y')}){win}")
            else:
                lines.append(f"  [{t:5.1f}s] key {d.get('key', '')}{win}")
        if len(self._events) > 40:
            lines.append(f"  …and {len(self._events) - 40} more events.")
        return "Recorded workflow:\n" + "\n".join(lines)
