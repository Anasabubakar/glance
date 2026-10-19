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


def test_cloud_is_paused_and_models_are_fast(monkeypatch):
    import sys
    sys.path.insert(0, "glance/shell")
    from config import Config
    for k in ("GLANCE_CLOUD", "GLANCE_ACTIVE_LLM", "GLANCE_ACTIVE_MODEL", "GLANCE_VISION_MODEL",
              "GLANCE_PROVIDER_ORDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
              "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    c = Config()
    c.custom_base_url = c.custom_model = ""
    assert "cloud" not in c.available_llm_providers()
    monkeypatch.setenv("GLANCE_ACTIVE_LLM", "cloud")      # stale saved choice is ignored
    assert c.llm_provider() != "cloud"
    monkeypatch.setenv("GLANCE_CLOUD", "1")
    assert "cloud" in c.available_llm_providers()
    monkeypatch.delenv("GLANCE_CLOUD")
    monkeypatch.delenv("GLANCE_ACTIVE_LLM")
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert c.vision_model() == "gpt-4o-mini"
    monkeypatch.delenv("OPENAI_API_KEY")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert "haiku" in c.vision_model()
