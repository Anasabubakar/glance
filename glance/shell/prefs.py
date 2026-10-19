"""
prefs.py — the user-facing on/off preferences, in ONE place.

The Settings page, the tray menu and the running app all read and write through
here, so they can never disagree (before this, the Settings page wrote
environment variables that nothing read, and showed wrong defaults).

Each preference has a real default (matching the app's behaviour), is persisted
to the user's .env, and is applied live to the running companion when there is
one.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Pref:
    env: str
    label: str
    desc: str
    default: bool
    group: str


PREFS = [
    Pref("GLANCE_WAKE_WORD", "Wake word",
         "Say “Glance” to talk hands-free. Turn off to use only the hotkey.", True, "Listening"),
    Pref("GLANCE_WEB_SEARCH", "Web search",
         "Let Glance look things up online when it needs fresh information.", True, "Assistance"),
    Pref("GLANCE_CODE_MODE", "Code mode",
         "Automatically adapt answers when you're in an editor or terminal.", True, "Assistance"),
    Pref("GLANCE_FALLBACK", "Fallback providers",
         "If your chosen AI is busy or out of quota, quietly try your other providers.", True, "Assistance"),
    Pref("GLANCE_MULTILINGUAL", "Multilingual",
         "Understand and reply in the language you speak.", True, "Assistance"),
    Pref("GLANCE_OCR_FALLBACK", "Read screen text",
         "Use text recognition on the screen when a vision model isn't available.", True, "Assistance"),
    Pref("GLANCE_SLOW_MODE", "Teacher pace",
         "Slower, more deliberate pointing and pauses. Good for learning.", False, "Learning"),
    Pref("GLANCE_CONFIRM_RISKY", "Confirm risky actions",
         "Ask before Glance sends, deletes, pays for or posts anything.", True, "Privacy"),
    Pref("GLANCE_PRIVACY", "Privacy guard",
         "Don't send screenshots of sensitive windows such as password managers and banks.", True, "Privacy"),
    Pref("GLANCE_JOURNAL", "Keep a journal",
         "Save your conversations locally so Glance can remember context.", True, "Privacy"),
]
_BY_ENV = {p.env: p for p in PREFS}

# Filled in by main.py once the companion is running: {"tray": ..., "manager": ...}
runtime: dict = {}


def groups() -> list:
    """[(group name, [Pref...])] in display order."""
    out: dict = {}
    for p in PREFS:
        out.setdefault(p.group, []).append(p)
    return list(out.items())


def get(env: str) -> bool:
    p = _BY_ENV[env]
    raw = os.environ.get(env, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return p.default


def persist(env: str, on: bool) -> None:
    """Remember the choice across launches (does not touch the running app)."""
    os.environ[env] = "1" if on else "0"
    try:
        from config import cfg
        cfg._persist_env(env, "1" if on else "0")
    except Exception:
        pass


def set_pref(env: str, on: bool) -> None:
    """Persist, then apply to the running companion if there is one."""
    persist(env, on)
    tray = runtime.get("tray")
    if tray is not None:
        try:
            tray.set_pref(env, on)      # updates the menu AND emits to the manager
        except Exception:
            pass


def apply_saved() -> None:
    """At startup: push any saved non-default choices into the running app."""
    tray = runtime.get("tray")
    if tray is None:
        return
    for p in PREFS:
        if os.environ.get(p.env, "").strip() and get(p.env) != p.default:
            try:
                tray.set_pref(p.env, get(p.env))
            except Exception:
                pass
