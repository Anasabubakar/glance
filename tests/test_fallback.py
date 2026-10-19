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
    monkeypatch.setattr(fp, "make_provider", lambda n, k=None: provs[n])
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


_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY",
         "GROQ_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_API_KEYS", "ANTHROPIC_API_KEYS",
         "OPENAI_API_KEYS", "GROQ_API_KEYS", "OPENROUTER_API_KEYS", "GLANCE_ACTIVE_LLM",
         "GLANCE_PROVIDER_ORDER", "GLANCE_FALLBACK", "GLANCE_CLOUD")


def _clean(monkeypatch):
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)


def test_every_provider_can_hold_several_keys(monkeypatch):
    from config import Config
    _clean(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "a")
    monkeypatch.setenv("GOOGLE_API_KEYS", "b, c\nA,a")
    monkeypatch.setenv("GROQ_API_KEY", "g1")
    monkeypatch.setenv("GROQ_API_KEYS", "g2")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "c1")
    monkeypatch.setenv("ANTHROPIC_API_KEYS", "c2,c3")
    c = Config()
    assert c.keys_for("gemini") == ["a", "b", "c", "A"]
    assert c.keys_for("groq") == ["g1", "g2"]
    assert c.keys_for("claude") == ["c1", "c2", "c3"]


def test_user_priority_order(monkeypatch):
    from config import Config
    _clean(monkeypatch)
    for k, v in (("GOOGLE_API_KEY", "a"), ("GROQ_API_KEY", "g"), ("ANTHROPIC_API_KEY", "c")):
        monkeypatch.setenv(k, v)
    c = Config()
    c._persist_env = lambda *a, **k: None
    assert c.llm_provider() == "claude"                      # automatic order until the user picks
    c.set_order(["groq", "gemini"])                          # claude not chosen: not used
    assert c.provider_order() == ["groq", "gemini"] and c.llm_provider() == "groq"
    c.move_provider("gemini", -1)
    assert c.provider_order() == ["gemini", "groq"]
    assert c.toggle_provider("claude") is True and c.provider_order() == ["gemini", "groq", "claude"]
    assert c.toggle_provider("groq") is False and c.provider_order() == ["gemini", "claude"]
    assert c.fallback_chain() == ["gemini", "claude"]
    monkeypatch.setenv("GLANCE_FALLBACK", "0")
    assert c.fallback_chain() == ["gemini"]
    c.set_active_llm("claude")                               # switching makes it priority 1
    assert c.provider_order()[0] == "claude"
