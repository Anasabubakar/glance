"""
FallbackProvider — tries the user's providers in priority order, and for providers with
several API keys, each key in turn. If one fails (busy, out of quota, bad key, down)
the next one answers, so a request doesn't just fail.

Only switches before any text has been produced, so a reply is never half one model
and half another. Providers after the first use their own default model.
"""

import time
from typing import AsyncIterator, List

from ai.base_provider import BaseLLMProvider, Message
from config import cfg

_KEYED_HERE = ("claude", "openai", "groq", "openrouter")   # Gemini rotates its own keys


def make_provider(name: str, key: str | None = None) -> BaseLLMProvider:
    if name == "claude":
        from ai.claude_provider import ClaudeProvider
        return ClaudeProvider(key)
    if name == "openai":
        from ai.openai_provider import OpenAIProvider
        return OpenAIProvider(key)
    if name == "gemini":
        from ai.gemini_provider import GeminiProvider
        return GeminiProvider()
    if name == "groq":
        from ai.openai_compat import GroqProvider
        return GroqProvider(key)
    if name == "openrouter":
        from ai.openai_compat import OpenRouterProvider
        return OpenRouterProvider(key)
    if name == "copilot":
        from ai.github_copilot_provider import GitHubCopilotProvider
        return GitHubCopilotProvider()
    if name == "custom":
        from ai.custom_provider import CustomProvider
        return CustomProvider()
    if name == "ollama":
        try:
            from companion_manager import _ensure_ollama_running
            _ensure_ollama_running()
        except Exception:
            pass
        from ai.ollama_provider import OllamaProvider
        return OllamaProvider()
    raise ValueError(name)


def _kid(key) -> str:
    import hashlib
    return hashlib.sha1((key or "").encode()).hexdigest()[:6]


class FallbackProvider(BaseLLMProvider):
    COOLDOWN = 60.0

    def __init__(self, names: list, log=None):
        self._names = list(names)
        self._log = log or (lambda m: print(m, flush=True))
        self._made: dict = {}
        self._cool: dict = {}
        self._turn = 0

    def _entries(self) -> list:
        """(provider, key) attempts in priority order, skipping ones that just failed."""
        self._turn += 1
        out = []
        for name in self._names:
            keys = cfg.keys_for(name) if name in _KEYED_HERE else []
            if len(keys) > 1:                         # spread load over the keys
                s = self._turn % len(keys)
                keys = keys[s:] + keys[:s]
            for k in (keys or [None]):
                out.append((name, k))
        now = time.monotonic()
        ready = [e for e in out if self._cool.get((e[0], _kid(e[1])), 0) <= now]
        return ready or out

    def _get(self, name: str, key) -> BaseLLMProvider:
        k = (name, _kid(key))
        if k not in self._made:
            self._made[k] = make_provider(name, key)
        return self._made[k]

    def _failed(self, entry, exc, nxt) -> None:
        self._cool[(entry[0], _kid(entry[1]))] = time.monotonic() + self.COOLDOWN
        self._log(f"[glance] {entry[0]} failed ({type(exc).__name__}); "
                  + (f"trying {nxt[0]}" if nxt else "no fallback left"))

    TOTAL_BUDGET = 28.0          # the whole chain gives up after this many seconds
    FIRST_TOKEN = 10.0           # a provider that has not started answering by then is skipped

    async def stream_response(self, user_text: str, screenshots_b64: List[str],
                              history: List[Message], system_prompt: str,
                              model: str | None = None) -> AsyncIterator[str]:
        import asyncio
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.TOTAL_BUDGET
        entries = self._entries()
        last: Exception | None = None
        for i, e in enumerate(entries):
            left = deadline - loop.time()
            if left < 2.5:
                break
            m = model if e[0] == self._names[0] else None
            try:
                prov = self._get(*e)
                if e[0] == "gemini" and hasattr(prov, "complete"):
                    # Race the two best Gemini models and take the first full answer: steadier
                    # than streaming from one model that may be slow or overloaded.
                    text = await asyncio.wait_for(
                        prov.complete(user_text, screenshots_b64, history, system_prompt, m,
                                      budget=min(18.0, left - 1.0), max_tokens=1024),
                        timeout=left)
                    yield text
                    return
                it = prov.stream_response(user_text, screenshots_b64, history, system_prompt, m).__aiter__()
                first = await asyncio.wait_for(it.__anext__(), timeout=min(self.FIRST_TOKEN, left))
                yield first
                async for chunk in it:
                    yield chunk
                return
            except StopAsyncIteration:
                return
            except Exception as exc:
                last = exc
                self._failed(e, exc, entries[i + 1] if i + 1 < len(entries) else None)
        raise last or RuntimeError("Every AI provider is busy right now. Try again in a moment.")

    async def complete(self, user_text: str, screenshots_b64: List[str], history: List[Message],
                       system_prompt: str, model: str | None = None) -> str:
        entries = self._entries()
        last: Exception | None = None
        for i, e in enumerate(entries):
            m = model if e[0] == self._names[0] else None
            try:
                prov = self._get(*e)
                if hasattr(prov, "complete"):
                    return await prov.complete(user_text, screenshots_b64, history,
                                               system_prompt, m)
                out = ""
                async for c in prov.stream_response(user_text, screenshots_b64, history,
                                                    system_prompt, m):
                    out += c
                if out.strip():
                    return out
                raise RuntimeError("empty answer")
            except Exception as exc:
                last = exc
                self._failed(e, exc, entries[i + 1] if i + 1 < len(entries) else None)
        raise last or RuntimeError("no provider available")

    async def health_check(self) -> bool:
        try:
            return await self._get(*self._entries()[0]).health_check()
        except Exception:
            return False
