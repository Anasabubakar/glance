"""Bring-your-own-endpoint provider: any OpenAI-compatible /chat/completions
server (OpenRouter, Groq, Together, LM Studio, vLLM, remote Ollama /v1, ...).
Also backs the free "cloud" tier. Stdlib only."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .base import LLMProvider

CLOUD_URL = "https://llm.anasmasama.dev"


def _post(url: str, payload: dict, key: str, timeout: int = 180, retries: int = 0) -> dict:
    """POST JSON; retry on 429 (shared free tier has a single slot) with backoff."""
    for attempt in range(retries + 1):
        try:
            return _post_once(url, payload, key, timeout)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries:
                raise
            time.sleep(min(5 * (attempt + 1), 20))


def _post_once(url: str, payload: dict, key: str, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key or 'none'}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


class CustomProvider(LLMProvider):
    name = "custom"
    _retries = 0

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None):
        self._base = (base_url or os.environ.get("GLANCE_CUSTOM_BASE_URL", "")).rstrip("/")
        self._key = api_key if api_key is not None else os.environ.get("GLANCE_CUSTOM_API_KEY", "")
        self._model = model or os.environ.get("GLANCE_CUSTOM_MODEL", "")
        if not self._base or not self._model:
            raise RuntimeError("Set GLANCE_CUSTOM_BASE_URL and GLANCE_CUSTOM_MODEL "
                               "(and GLANCE_CUSTOM_API_KEY if the endpoint needs one).")

    def complete(self, system: str, user: str) -> str:
        payload = {"model": self._model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}],
                   "response_format": {"type": "json_object"}}
        try:
            data = _post(f"{self._base}/chat/completions", payload, self._key,
                         retries=self._retries)
        except urllib.error.HTTPError as e:
            if e.code != 400:      # some servers reject response_format; retry without
                raise
            payload.pop("response_format")
            data = _post(f"{self._base}/chat/completions", payload, self._key,
                         retries=self._retries)
        return data["choices"][0]["message"]["content"] or ""


class CloudProvider(CustomProvider):
    """Free hosted text model. Mints a rate-limited key on first use."""
    name = "cloud"
    _retries = 8

    def __init__(self, model: str | None = None):
        base = os.environ.get("GLANCE_CLOUD_URL", CLOUD_URL).rstrip("/")
        key = os.environ.get("GLANCE_CLOUD_KEY", "")
        if not key:
            key = self._register(base)
        super().__init__(model="glance", base_url=f"{base}/v1", api_key=key)

    @staticmethod
    def _register(base: str) -> str:
        key = _post(f"{base}/register", {}, "", timeout=15)["api_key"]
        os.environ["GLANCE_CLOUD_KEY"] = key
        env = Path.home() / ".glance" / ".env"
        env.parent.mkdir(parents=True, exist_ok=True)
        with env.open("a", encoding="utf-8") as f:
            f.write(f"\nGLANCE_CLOUD_KEY={key}\n")
        return key
