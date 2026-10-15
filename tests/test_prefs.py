"""Preferences: real defaults, persistence helpers, hotkey parsing."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import prefs  # noqa: E402


def test_defaults_match_the_app(monkeypatch):
    for p in prefs.PREFS:
        monkeypatch.delenv(p.env, raising=False)
    assert prefs.get("GLANCE_WAKE_WORD") is True        # app default is ON
    assert prefs.get("GLANCE_PRIVACY") is True
    assert prefs.get("GLANCE_SLOW_MODE") is False


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("GLANCE_WAKE_WORD", "0")
    monkeypatch.setenv("GLANCE_SLOW_MODE", "1")
    assert prefs.get("GLANCE_WAKE_WORD") is False
    assert prefs.get("GLANCE_SLOW_MODE") is True


def test_groups_cover_every_pref():
    flat = [p.env for _g, items in prefs.groups() for p in items]
    assert sorted(flat) == sorted(p.env for p in prefs.PREFS)
