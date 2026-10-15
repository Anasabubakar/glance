"""Gemini model selection must survive Google retiring model names."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

from ai.gemini_models import pick_models  # noqa: E402


def _ms(*names):
    return [{"name": "models/" + n, "supportedGenerationMethods": ["generateContent"]} for n in names]


def test_prefers_newest_stable_flash_and_skips_special_models():
    out = pick_models(_ms("gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.8-flash",
                          "gemini-3.8-flash-lite-tts", "gemini-3.1-flash-image",
                          "gemini-3-flash-preview", "gemini-flash-latest",
                          "gemini-3.5-flash-lite", "gemini-pro-latest"))
    assert out[0] == "gemini-3.8-flash"
    assert out[1] == "gemini-3.5-flash"
    assert "gemini-flash-latest" in out[:3]          # always-valid alias reachable early
    assert not any(("tts" in n or "image" in n or "preview" in n) for n in out)
    assert "gemini-3.5-flash-lite" in out            # lite only as a late fallback
    assert out.index("gemini-3.5-flash-lite") > out.index("gemini-2.5-flash")


def test_models_without_generate_content_are_ignored():
    ms = [{"name": "models/gemini-9-flash", "supportedGenerationMethods": ["embedContent"]}]
    assert "gemini-9-flash" not in pick_models(ms)


def test_empty_list_still_gives_working_aliases():
    assert pick_models([]) == ["gemini-flash-latest", "gemini-flash-lite-latest"]
