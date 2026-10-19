"""
registry.py — the automation rulebook. Handlers register a pattern; the dispatcher tries
them in priority order and the first that returns a Result wins. A handler returns None
to say "not mine", so the request moves on (and finally to the AI).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .nlp import words_to_numbers


@dataclass
class Result:
    say: str = ""          # spoken/shown confirmation ("" = silent)
    ok: bool = True


_RULES: list = []          # (prio, compiled, fn, name)

_LEAD = re.compile(
    r"^(?:(?:hey|ok|okay|yo)[ ,]+)?(?:glance[ ,]+)?(?:(?:please|can you|could you|would you|will you|"
    r"i want you to|i need you to|go ahead and|i'd like you to|i would like you to|let's|lets)[ ,]+)*"
    r"(?:please[ ,]+)?", re.I)
_TAIL = re.compile(r"[\s.!?,]*(?:please|for me|now|thanks|thank you|right now|real quick)?[\s.!?,]*$", re.I)


def clean(text: str) -> str:
    t = (text or "").strip()
    for _ in range(2):
        t = _LEAD.sub("", t)
    t = _TAIL.sub("", t).strip()
    return t


_DRY: dict = {}            # rule name -> fn(text) -> bool, for catch-all rules that can't be judged by regex


def rule(pattern: str, name: str = "", prio: int = 50, numbers: bool = True, dry=None):
    """Register `fn(ctx, match, text)`. The text is lower-cased, cleaned of politeness and,
    unless numbers=False, has number words turned into digits."""
    rx = re.compile(pattern, re.I)

    def deco(fn: Callable):
        _RULES.append((prio, rx, fn, name or fn.__name__, numbers))
        if dry:
            _DRY[name or fn.__name__] = dry
        _RULES.sort(key=lambda r: r[0])
        return fn
    return deco


def rules() -> list:
    return list(_RULES)


_SPLIT = re.compile(r"\s*(?:,?\s+and then\s+|,?\s+then\s+|,?\s+after that\s+|;\s*|,?\s+and\s+(?=(?:open|close|minimi[sz]e|maximi[sz]e|"
                    r"switch|go|search|play|pause|mute|set|turn|type|press|scroll|take|show|lock|copy|paste|"
                    r"volume|launch|start|tile|move|draw|run|remind|what)\b))", re.I)


_META = re.compile(r"^(?:(?:create|make|save|add|set up|new)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:routine|automation|workflow)|"
                   r"when i say|(?:every|each)\s|remind me|(?:in|after)\s+\d|at\s+\d|tomorrow at|"
                   r"(?:set\s+)?(?:an?\s+)?(?:timer|alarm)|start recording|stop recording|(?:add|create|schedule|book)\s+.+\s+(?:to|on|in)\s+my\s+calendar|"
                   r"(?:send|write|email|draft)\s+.*\b(?:email|mail)\b|translate\s|(?:search|play|find)\b.+\b(?:and|then)\b)", re.I)


def split_compound(s: str) -> list:
    if _META.match(s):
        return [s]                          # a definition or one request that merely contains "and"
    parts = [p.strip() for p in _SPLIT.split(s) if p and p.strip()]
    return parts if len(parts) > 1 else [s]


def handle_one(ctx, s: str):
    low = s.lower()
    for _prio, rx, fn, _name, numbers in _RULES:
        text = words_to_numbers(low) if numbers else low
        m = rx.match(text)
        if m:
            try:
                res = fn(ctx, m, text)
            except Exception as e:                  # a handler bug must not break the request
                from session_log import slog
                slog("ERROR", f"automation {fn.__name__}: {type(e).__name__}: {e}")
                res = None
            if res is not None:
                return res
    return None


def handle(ctx, text: str):
    """Run a request entirely with automations. Returns a Result, or None if any part of it
    needs the AI (nothing is done in that case)."""
    s = clean(text)
    if not s:
        return None
    parts = split_compound(s)
    if len(parts) == 1:
        return handle_one(ctx, s)
    # Compound: only run it if EVERY part is understood, so we never do half of a request.
    if not all(_understood(p) for p in parts):
        return handle_one(ctx, s)          # maybe a single rule covers the whole sentence
    said = []
    for p in parts:
        r = handle_one(ctx, p)
        if r is None:
            return Result(" ".join(said), ok=False) if said else None
        if r.say:
            said.append(r.say)
    return Result(" ".join(said[-2:]))


def understands(text: str) -> bool:
    """True if the automations can handle this whole request (every part of it)."""
    s = clean(text)
    if not s:
        return False
    parts = split_compound(s)
    return all(_understood(p) for p in parts)


def _understood(part: str) -> bool:
    low = part.lower()
    for _p, rx, _f, name, numbers in _RULES:
        text = words_to_numbers(low) if numbers else low
        if name in _DRY:
            if _DRY[name](text):
                return True
        elif rx.match(text):
            return True
    return False
