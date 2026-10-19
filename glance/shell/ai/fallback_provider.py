"""
FallbackProvider — if the chosen provider fails (busy, out of quota, down), quietly
try the next provider the user has set up, so a request doesn't just fail.

Only switches before any text has been produced, so a reply is never half one model
and half another. Fallback providers use their own default model.
"""

from typing import AsyncIterator, List

from ai.base_provider import BaseLLMProvider, Message


def make_provider(name: str) -> BaseLLMProvider:
    if name == "claude":
        from ai.claude_provider import ClaudeProvider
        return ClaudeProvider()
    if name == "openai":
        from ai.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "gemini":
        from ai.gemini_provider import GeminiProvider
        return GeminiProvider()
    if name == "groq":
        from ai.openai_compat import GroqProvider
        return GroqProvider()
    if name == "openrouter":
        from ai.openai_compat import OpenRouterProvider
        return OpenRouterProvider()
    if name == "custom":
        from ai.custom_provider import CustomProvider
        return CustomProvider()
    raise ValueError(name)


class FallbackProvider(BaseLLMProvider):
    def __init__(self, names: list, log=None):
        self._names = list(names)
        self._log = log or (lambda m: print(m, flush=True))
        self._made: dict = {}

    def _get(self, name: str) -> BaseLLMProvider:
        if name not in self._made:
            self._made[name] = make_provider(name)
        return self._made[name]

    async def stream_response(self, user_text: str, screenshots_b64: List[str],
                              history: List[Message], system_prompt: str,
                              model: str | None = None) -> AsyncIterator[str]:
        last: Exception | None = None
        for i, name in enumerate(self._names):
            started = False
            try:
                prov = self._get(name)
                async for chunk in prov.stream_response(
                        user_text, screenshots_b64, history, system_prompt,
                        model if i == 0 else None):
                    started = True
                    yield chunk
                return
            except Exception as e:
                if started:
                    raise                      # never splice two models into one reply
                last = e
                nxt = self._names[i + 1] if i + 1 < len(self._names) else None
                self._log(f"[glance] {name} failed ({type(e).__name__}); "
                          + (f"trying {nxt}" if nxt else "no fallback left"))
        if last:
            raise last

    async def complete(self, user_text: str, screenshots_b64: List[str], history: List[Message],
                       system_prompt: str, model: str | None = None) -> str:
        last: Exception | None = None
        for i, name in enumerate(self._names):
            try:
                prov = self._get(name)
                if hasattr(prov, "complete"):
                    return await prov.complete(user_text, screenshots_b64, history,
                                               system_prompt, model if i == 0 else None)
                out = ""
                async for c in prov.stream_response(user_text, screenshots_b64, history,
                                                    system_prompt, model if i == 0 else None):
                    out += c
                if out.strip():
                    return out
                raise RuntimeError("empty answer")
            except Exception as e:
                last = e
                nxt = self._names[i + 1] if i + 1 < len(self._names) else None
                self._log(f"[glance] {name} failed ({type(e).__name__}); "
                          + (f"trying {nxt}" if nxt else "no fallback left"))
        raise last or RuntimeError("no provider available")

    async def health_check(self) -> bool:
        try:
            return await self._get(self._names[0]).health_check()
        except Exception:
            return False
