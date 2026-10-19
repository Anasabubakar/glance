"""Groq and OpenRouter: OpenAI-compatible hosts with free tiers, used as a main
provider or as a fallback when another provider is busy or out of quota."""

from ai.custom_provider import CustomProvider
from config import cfg

GROQ_URL = "https://api.groq.com/openai/v1"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
GROQ_TEXT = "llama-3.3-70b-versatile"
GROQ_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
OPENROUTER_FREE = "openrouter/free"        # OpenRouter's router over its free models


class GroqProvider(CustomProvider):
    def __init__(self):
        super().__init__(base_url=GROQ_URL, api_key=cfg.groq_api_key, model=GROQ_TEXT)

    async def stream_response(self, user_text, screenshots_b64, history, system_prompt, model=None):
        # Only the Llama 4 models on Groq accept images; use one when there is a screenshot.
        if screenshots_b64 and (not model or "llama-4" not in model):
            model = GROQ_VISION
        elif not screenshots_b64 and not model:
            model = GROQ_TEXT
        async for c in super().stream_response(user_text, screenshots_b64, history,
                                               system_prompt, model):
            yield c


class OpenRouterProvider(CustomProvider):
    def __init__(self):
        super().__init__(base_url=OPENROUTER_URL, api_key=cfg.openrouter_api_key,
                         model=OPENROUTER_FREE)

    async def stream_response(self, user_text, screenshots_b64, history, system_prompt, model=None):
        async for c in super().stream_response(user_text, screenshots_b64, history,
                                               system_prompt, model or OPENROUTER_FREE):
            yield c
