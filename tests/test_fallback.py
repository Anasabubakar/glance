import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

from ai import fallback_provider as fp  # noqa: E402
from ai import gemini_provider as gp  # noqa: E402


class _Boom:
    async def stream_response(self, *a, **k):
        raise RuntimeError("429")
        yield ""


class _Ok:
    def __init__(self, text):
        self.text = text

    async def stream_response(self, *a, **k):
        yield self.text


def _chain(monkeypatch, provs):
    monkeypatch.setattr(fp, "make_provider", lambda n: provs[n])
    return fp.FallbackProvider(list(provs), log=lambda m: None)


def test_falls_back_when_first_provider_fails(monkeypatch):
    f = _chain(monkeypatch, {"gemini": _Boom(), "groq": _Ok("hi from groq")})

    async def go():
        return "".join([c async for c in f.stream_response("x", [], [], "s")])
    assert asyncio.run(go()) == "hi from groq"
    assert asyncio.run(f.complete("x", [], [], "s")) == "hi from groq"


def test_last_error_is_raised_when_all_fail(monkeypatch):
    f = _chain(monkeypatch, {"gemini": _Boom(), "groq": _Boom()})
    try:
        asyncio.run(f.complete("x", [], [], "s"))
    except RuntimeError as e:
        assert "429" in str(e)
    else:
        raise AssertionError("expected an error")


def test_gemini_pairs_rotate_keys_and_skip_cooled(monkeypatch):
    monkeypatch.setattr(gp, "_save_health", lambda: None)
    gp._cool.clear(); gp._bad_until.clear()
    keys = ["k-one", "k-two", "k-three"]
    pairs = gp._pairs(["m1", "m2"], keys)
    assert {k for _m, k in pairs} == set(keys) and len(pairs) == 6
    gp._cooldown("m1", 429, None, "k-two")           # quota hit on k-two for m1 only
    pairs = gp._pairs(["m1", "m2"], keys)
    assert ("m1", "k-two") not in pairs and ("m2", "k-two") in pairs
    gp._cool.clear(); gp._bad_until.clear()


def test_config_collects_multiple_gemini_keys(monkeypatch):
    from config import Config
    c = Config()
    c.google_api_key = "a"
    c.google_api_keys_extra = "b, c\nA,a"
    assert c.gemini_keys() == ["a", "b", "c", "A"]
    c.groq_api_key = "g"
    c.anthropic_api_key = c.openai_api_key = None
    monkeypatch.setenv("GLANCE_ACTIVE_LLM", "gemini")
    assert c.fallback_chain()[:2] == ["gemini", "groq"]
    monkeypatch.setenv("GLANCE_FALLBACK", "0")
    assert c.fallback_chain() == ["gemini"]
