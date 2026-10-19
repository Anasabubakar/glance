"""Groq and OpenRouter: OpenAI-compatible hosts with free tiers, used as a main
provider or as a fallback when another provider is busy or out of quota."""

from ai.custom_provider import CustomProvider
from config import cfg

GROQ_URL = "https://api.groq.com/openai/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
GROQ_TEXT = "llama-3.3-70b-versatile"
GROQ_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
OPENROUTER_FREE = "openrouter/free"        # OpenRouter's router over its free models


_groq_cache: dict = {"t": 0.0, "ids": []}
_TEXT_PREF = ("openai/gpt-oss-20b", "llama-3.1-8b-instant", "llama-3.3-70b-versatile",
              "openai/gpt-oss-120b", "qwen", "llama")


async def _groq_models(key: str) -> list:
    """The models THIS key can use (Groq changes its lineup often; a fixed name 404s)."""
    import time
    import httpx
    if _groq_cache["ids"] and time.monotonic() - _groq_cache["t"] < 3600:
        return _groq_cache["ids"]
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{GROQ_URL}/models", headers={"Authorization": f"Bearer {key}"})
        ids = [m["id"] for m in r.json().get("data", []) if m.get("active", True)
               and not any(x in m["id"] for x in ("whisper", "tts", "playai", "guard", "orpheus", "distil", "allam"))]
        if ids:
            _groq_cache.update(t=time.monotonic(), ids=ids)
            return ids
    except Exception:
        pass
    return _groq_cache["ids"] or [GROQ_TEXT]


def _pick_groq(ids: list, vision: bool, wanted: str | None):
    if wanted and wanted in ids:
        return wanted
    if vision:
        return next((i for i in ids if "llama-4" in i or "vision" in i or "-vl" in i), None)
    for pref in _TEXT_PREF:
        hit = next((i for i in ids if i == pref or (pref in i and "/" not in pref)), None)
        if hit:
            return hit
    return ids[0] if ids else None


class GroqProvider(CustomProvider):
    def __init__(self, api_key: str | None = None):
        super().__init__(base_url=GROQ_URL, api_key=api_key or cfg.groq_api_key, model=GROQ_TEXT)
        self._key = api_key or cfg.groq_api_key or ""

    async def stream_response(self, user_text, screenshots_b64, history, system_prompt, model=None):
        ids = await _groq_models(self._key)
        chosen = _pick_groq(ids, bool(screenshots_b64), model)
        if chosen is None:
            raise RuntimeError("Groq has no model that can see images for this key")
        async for c in super().stream_response(user_text, screenshots_b64, history,
                                               system_prompt, chosen):
            yield c


class OpenRouterProvider(CustomProvider):
    def __init__(self, api_key: str | None = None):
        super().__init__(base_url=OPENROUTER_URL, api_key=api_key or cfg.openrouter_api_key,
                         model=OPENROUTER_FREE)

    async def stream_response(self, user_text, screenshots_b64, history, system_prompt, model=None):
        async for c in super().stream_response(user_text, screenshots_b64, history,
                                               system_prompt, model or OPENROUTER_FREE):
            yield c
