"""
Google Gemini provider — uses the REST SSE streaming API directly (no extra deps).
The model is chosen at runtime from what the key can actually use (see
ai/gemini_models.py), because Google retires model names often.
"""

import asyncio
import json
import os
import time
from typing import AsyncIterator, List

import httpx

from ai.base_provider import BaseLLMProvider, Message
from ai.gemini_models import pick_models
from config import cfg

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Process-wide: models that returned 404/403 for this key are not retried, and the
# live model list is refreshed at most every 6 hours.
_bad: set = set()
_cache = {"t": 0.0, "models": []}


class GeminiError(RuntimeError):
    """A Gemini failure with a message that never contains the API key."""


def _hdr(key: str) -> dict:
    return {"x-goog-api-key": key or "", "Content-Type": "application/json"}


def _err_text(resp_text: str, key: str) -> str:
    try:
        msg = json.loads(resp_text)["error"]["message"]
    except Exception:
        msg = resp_text
    return " ".join(str(msg).replace(key or "\0", "***").split())[:240]


# Per-model health: free-tier keys are rate limited PER MODEL (429) and new models
# are often overloaded (503). A failed model sits out for a short cooldown, and the
# model that last worked is tried first, so a turn doesn't re-pay for known failures.
_cool: dict = {}
_nothink: set = set()        # models that reject thinkingConfig
_sticky = {"text": None, "vision": None}


def _cooldown(name: str, status: int, retry_after: str | None) -> None:
    secs = 20.0
    if status == 503:
        secs = 8.0
    elif status == 0:
        secs = 5.0
    try:
        if retry_after:
            secs = min(max(float(retry_after), 2.0), 90.0)
    except ValueError:
        pass
    _cool[name] = time.monotonic() + secs


def _order(cands: list, vision: bool) -> list:
    now = time.monotonic()
    if vision:                                  # lite models mis-place clicks: never use them
        cands = [c for c in cands if "lite" not in c]
    ready = [c for c in cands if _cool.get(c, 0) <= now]
    pool = ready or sorted(cands, key=lambda c: _cool.get(c, 0))
    pref = _sticky["vision" if vision else "text"]
    if pref in pool:
        pool = [pref] + [c for c in pool if c != pref]
    return pool


async def _candidates(client: httpx.AsyncClient, key: str, requested: str | None) -> list:
    if time.monotonic() - _cache["t"] > 6 * 3600 or not _cache["models"]:
        try:
            r = await client.get(f"{BASE}/models?pageSize=200", headers=_hdr(key), timeout=15)
            if r.status_code == 200:
                _cache["models"] = pick_models(r.json().get("models", []))
                _cache["t"] = time.monotonic()
        except Exception:
            pass
    order = ([requested] if requested and requested not in ("auto",) else []) + \
            (_cache["models"] or pick_models([]))
    seen, out = set(), []
    for m in order:
        if m and m not in seen and m not in _bad:
            seen.add(m); out.append(m)
    return out[:8]


class GeminiProvider(BaseLLMProvider):

    def __init__(self):
        self._api_key = cfg.google_api_key

    async def stream_response(
        self,
        user_text: str,
        screenshots_b64: List[str],
        history: List[Message],
        system_prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        parts: list = []
        for img_b64 in screenshots_b64:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
        parts.append({"text": user_text})
        contents.append({"role": "user", "parts": parts})

        body = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            # Spoken replies and UI grounding don't need long "thinking": turning it
            # off cuts roughly 2-3 s from every response. Dropped if a model rejects it.
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
        }
        if not screenshots_b64:
            # Plain chat doesn't need long "thinking": off saves ~2-3 s. Never for
            # screenshots: grounding (where to click) gets much less accurate.
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}

        last_err = "no usable Gemini model"
        async with httpx.AsyncClient(timeout=120) as client:
            # Google answers 503 "high demand" in short bursts that hit every model
            # at once; a brief backoff and a second pass rides them out.
            for attempt in range(3):
                retriable = False
                queue = _order(await _candidates(client, self._api_key, model), bool(screenshots_b64))
                while queue:
                    name = queue.pop(0)
                    url = f"{BASE}/models/{name}:streamGenerateContent?alt=sse"
                    _t0 = time.monotonic()
                    send = body
                    if name in _nothink and "thinkingConfig" in body["generationConfig"]:
                        send = {**body, "generationConfig": {k: v for k, v in
                                body["generationConfig"].items() if k != "thinkingConfig"}}
                    try:
                        cm = client.stream("POST", url, json=send, headers=_hdr(self._api_key))
                        resp = await cm.__aenter__()
                    except httpx.HTTPError as e:
                        last_err = f"{name}: network error {type(e).__name__}"
                        retriable = True
                        _cooldown(name, 0, None)
                        continue
                    try:
                        if os.environ.get("GLANCE_DEBUG_GEMINI"):
                            print(f"[gemini] {name} -> HTTP {resp.status_code} "
                                  f"after {time.monotonic() - _t0:.1f}s", flush=True)
                        if resp.status_code != 200:
                            text = (await resp.aread()).decode("utf-8", "replace")
                            last_err = f"{name}: HTTP {resp.status_code} {_err_text(text, self._api_key)}"
                            low = text.lower()
                            if resp.status_code in (401, 403) and "no longer available" not in low:
                                raise GeminiError(last_err)      # key rejected: don't loop
                            if resp.status_code == 400:
                                if "api key" in low:
                                    raise GeminiError(last_err)  # bad key: don't loop
                                if "thinkingConfig" in send["generationConfig"]:
                                    _nothink.add(name)           # remember; retry without it
                                    queue.insert(0, name)
                                else:
                                    _bad.add(name)               # this model rejects us; skip it
                                continue
                            if resp.status_code in (403, 404):
                                _bad.add(name)                   # retired for this key
                            elif resp.status_code in (429, 500, 502, 503, 504):
                                if resp.status_code != 429:
                                    retriable = True             # transient; a second pass may work
                                _cooldown(name, resp.status_code, resp.headers.get("retry-after"))
                            continue                             # try the next model
                        _sticky["vision" if screenshots_b64 else "text"] = name
                        _cool.pop(name, None)
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if not data or data == "[DONE]":
                                continue
                            try:
                                obj = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            for cand in obj.get("candidates", []):
                                for part in cand.get("content", {}).get("parts", []):
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        return
                    finally:
                        await cm.__aexit__(None, None, None)
                if not retriable:
                    break
                await asyncio.sleep(1.5 * (attempt + 1))
        if "HTTP 429" in last_err:
            raise GeminiError("Gemini is rate-limiting this key right now (free-tier "
                              "limit). Wait a minute, or enable billing for a higher limit. "
                              f"[{last_err}]")
        if "HTTP 503" in last_err:
            raise GeminiError("Gemini is overloaded right now. Try again in a moment. "
                              f"[{last_err}]")
        raise GeminiError(last_err)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{BASE}/models?pageSize=1", headers=_hdr(self._api_key))
                return r.status_code == 200
        except Exception:
            return False
