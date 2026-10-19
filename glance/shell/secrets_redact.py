"""
secrets_redact.py — API keys must never reach the console, the session log, a
diagnostics file or a bug report.

redact(text) masks (a) every key the user has configured, exactly, and (b) anything
that merely looks like a provider key. install() wraps stdout/stderr so a stray print
or traceback cannot leak one.
"""

from __future__ import annotations

import os
import re
import sys

_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),                 # Google API keys
    re.compile(r"AQ\.[0-9A-Za-z_\-]{25,}"),                 # newer Google keys
    re.compile(r"sk-ant-[0-9A-Za-z_\-]{20,}"),              # Anthropic
    re.compile(r"sk-or-v1-[0-9A-Za-z_\-]{20,}"),            # OpenRouter
    re.compile(r"sk-[0-9A-Za-z_\-]{24,}"),                  # OpenAI and friends
    re.compile(r"gsk_[0-9A-Za-z]{20,}"),                    # Groq
    re.compile(r"sk_[0-9a-f]{30,}"),                        # ElevenLabs
    re.compile(r"(?i)(bearer\s+)[0-9A-Za-z._\-]{20,}"),
    re.compile(r"(?i)((?:x-goog-api-key|x-api-key|api[_-]?key|token)['\"]?\s*[:=]\s*['\"]?)[0-9A-Za-z._\-]{16,}"),
]
_KEY_ENV = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY",
            "GROQ_API_KEY", "OPENROUTER_API_KEY", "DEEPGRAM_API_KEY", "ELEVENLABS_API_KEY",
            "TAVILY_API_KEY", "GLANCE_CUSTOM_API_KEY", "GLANCE_CLOUD_KEY")


def _configured_secrets() -> list:
    out = []
    for name in _KEY_ENV:
        for var in (name, name + "S"):
            for k in re.split(r"[,\s]+", os.environ.get(var, "")):
                if len(k) >= 12:
                    out.append(k)
    return sorted(set(out), key=len, reverse=True)


def mask(k: str) -> str:
    return (k[:2] + "…" + k[-3:]) if len(k) > 8 else "…"


def redact(text: str) -> str:
    if not text:
        return text
    for k in _configured_secrets():
        if k in text:
            text = text.replace(k, "[key " + mask(k) + "]")
    for rx in _PATTERNS:
        if rx.groups:
            text = rx.sub(lambda m: m.group(1) + "[key]", text)
        else:
            text = rx.sub(lambda m: "[key " + mask(m.group(0)) + "]", text)
    return text


class _Filter:
    def __init__(self, stream):
        self._s = stream

    def write(self, data):
        try:
            return self._s.write(redact(data) if isinstance(data, str) else data)
        except Exception:
            return 0

    def __getattr__(self, name):
        return getattr(self._s, name)


def install() -> None:
    for name in ("stdout", "stderr"):
        st = getattr(sys, name, None)
        if st is not None and not isinstance(st, _Filter):
            setattr(sys, name, _Filter(st))
