"""BYOK provider: any OpenAI-compatible endpoint the user points Glance at
(OpenRouter, Groq, Together, Fireworks, LM Studio, vLLM, a remote Ollama /v1...).
Configured by GLANCE_CUSTOM_BASE_URL / GLANCE_CUSTOM_API_KEY / GLANCE_CUSTOM_MODEL."""

from typing import AsyncIterator, List

from openai import AsyncOpenAI

from ai.base_provider import BaseLLMProvider, Message
from config import cfg

MAX_TOKENS = 1024


def build_messages(user_text, screenshots_b64, history, system_prompt, send_images=True):
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    if screenshots_b64 and send_images:
        content: list = [{"type": "image_url",
                          "image_url": {"url": f"data:image/jpeg;base64,{b}"}}
                         for b in screenshots_b64]
        content.append({"type": "text", "text": user_text})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_text})
    return messages


class CustomProvider(BaseLLMProvider):
    send_images = True
    max_retries = 2      # the SDK backs off and retries on 429/5xx

    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None):
        self._base_url = (base_url or cfg.custom_base_url).rstrip("/")
        self._model = model or cfg.custom_model
        # Local servers (LM Studio, Ollama) accept any non-empty key.
        self._client = AsyncOpenAI(base_url=self._base_url,
                                   api_key=(api_key or cfg.custom_api_key or "none"),
                                   max_retries=self.max_retries)

    async def stream_response(
        self,
        user_text: str,
        screenshots_b64: List[str],
        history: List[Message],
        system_prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=model or self._model,
            messages=build_messages(user_text, screenshots_b64, history,
                                    system_prompt, self.send_images),
            max_tokens=MAX_TOKENS,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
