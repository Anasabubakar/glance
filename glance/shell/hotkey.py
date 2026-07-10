import threading
from typing import Callable, Set

from pynput import keyboard

from config import cfg


class GlobalHotkeyMonitor:
    """
    Registers a system-wide hotkey (default: ctrl+alt+m).
    Fires on_press when held, on_release when released.
    Runs in a daemon thread so it doesn't block the Qt event loop.
    """

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        hotkey: str | None = None,
    ):
        self._hotkey = hotkey or cfg.hotkey
        self._on_press = on_press
        self._on_release = on_release
        self._held = False
        self._pressed_keys: Set[keyboard.KeyCode] = set()
        self._listener: keyboard.Listener | None = None

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press_event, 
            on_release=self._on_release_event
        )
        self._listener.start()

    def _on_press_event(self, key):
        self._pressed_keys.add(key)
        if not self._held and self._is_hotkey_pressed():
            self._held = True
            self._on_press()

    def _on_release_event(self, key):
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)
        if self._held and not self._is_hotkey_pressed():
            self._held = False
            self._on_release()

    def _is_hotkey_pressed(self) -> bool:
        parts = [p.strip().lower() for p in self._hotkey.split("+")]
        
        def check_key(p):
            if p == "ctrl":
                return any(k in self._pressed_keys for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
            if p == "alt":
                return any(k in self._pressed_keys for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r))
            if p == "shift":
                return any(k in self._pressed_keys for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r))
            if p == "win":
                return any(k in self._pressed_keys for k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r))
            
            # For characters, we check KeyCode
            char_key = keyboard.KeyCode.from_char(p[0]) if p else None
            if char_key and char_key in self._pressed_keys:
                return True
            
            # Also check if it's a special key like 'esc'
            try:
                special_key = getattr(keyboard.Key, p)
                return special_key in self._pressed_keys
            except AttributeError:
                pass
            
            return False

        return all(check_key(p) for p in parts)

    def stop(self):
        if self._listener:
            self._listener.stop()


class StopHotkey:
    """A global key that cancels the current generation (default: Esc).

    Only fires while Glance is actively talking/thinking — the callback itself
    should no-op when Glance is idle, so this can be left always-on without
    stealing Esc from other apps' UX.
    """

    def __init__(self, on_stop: Callable[[], None], key: str = "esc"):
        self._on_stop = on_stop
        self._key = key
        self._hotkeys = {f"<{self._key}>": self._on_stop}
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self):
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
