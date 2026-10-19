"""
nlp.py — tiny, fast, dependency-free language helpers for the automation engine:
number words, durations, dates/times ("tomorrow at 3pm"), fuzzy name matching.
"""

from __future__ import annotations

import datetime as dt
import difflib
import re

_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
          "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
          "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
          "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "a": 1, "an": 1,
          "half": 0.5, "couple": 2}
_WORDNUM = re.compile(r"\b(?:" + "|".join(sorted((k for k in _UNITS if k not in ("a", "an", "half", "couple")),
                                                key=len, reverse=True)) + r")(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?\b", re.I)


def words_to_numbers(text: str) -> str:
    """'set a timer for twenty five minutes' -> 'set a timer for 25 minutes'."""
    def repl(m):
        parts = re.split(r"[\s-]+", m.group(0).lower())
        total = sum(_UNITS.get(p, 0) for p in parts)
        return str(int(total)) if total == int(total) else str(total)
    return _WORDNUM.sub(repl, text)


def to_number(token: str):
    t = (token or "").strip().lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return float(t) if "." in t else int(t)
    if t in _UNITS:
        v = _UNITS[t]
        return int(v) if v == int(v) else v
    try:
        return int(words_to_numbers(t))
    except ValueError:
        return None


_DUR = re.compile(r"(?P<n>\d+(?:\.\d+)?|an?|half(?: an?)?|one|two|three|four|five|ten|fifteen|twenty|thirty)\s*"
                  r"(?P<u>seconds?|secs?|minutes?|mins?|hours?|hrs?|days?)\b", re.I)


def parse_duration(text: str):
    """Seconds in 'in 5 minutes', 'for an hour and 30 minutes', '2 hours'; None if absent."""
    t = words_to_numbers(text.lower())
    total, found = 0.0, False
    for m in _DUR.finditer(t):
        raw = m.group("n")
        n = 0.5 if raw.startswith("half") else (1 if raw in ("a", "an") else float(raw))
        u = m.group("u")
        total += n * (86400 if u.startswith("d") else 3600 if u.startswith(("h")) else 60 if u.startswith("m") else 1)
        found = True
    return int(total) if found else None


_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_clock(text: str):
    """(hour, minute) from '3pm', '3:30 pm', '15:30', 'noon', 'midnight', 'morning'... or None."""
    t = text.lower()
    if "noon" in t:
        return 12, 0
    if "midnight" in t:
        return 0, 0
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b", t)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)[0]
        if h == 12:
            h = 0
        return (h + (12 if ap == "p" else 0)) % 24, mi
    m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\bat (\d{1,2})\b", t)
    if m:
        h = int(m.group(1))
        return (h if h > 6 or h == 0 else h + 12), 0          # "at 5" means 5 pm, "at 9" means 9
    for word, hm in (("this morning", (9, 0)), ("morning", (9, 0)), ("afternoon", (15, 0)),
                     ("evening", (18, 0)), ("tonight", (20, 0)), ("night", (21, 0))):
        if word in t:
            return hm
    return None


def parse_when(text: str, now: dt.datetime | None = None):
    """A datetime for phrases like 'in 2 hours', 'tomorrow at 3pm', 'next monday 9am',
    'at 17:45', 'friday evening'. Returns None when no time is found."""
    now = now or dt.datetime.now()
    t = text.lower()
    secs = parse_duration(t) if re.search(r"\b(?:in|after|for)\b", t) else None
    if secs and not re.search(r"\b(?:at|tomorrow|next|on)\b", t):
        return now + dt.timedelta(seconds=secs)
    clock = parse_clock(t)
    day = None
    if "tomorrow" in t:
        day = now.date() + dt.timedelta(days=1)
    elif "day after tomorrow" in t:
        day = now.date() + dt.timedelta(days=2)
    elif "today" in t or "tonight" in t:
        day = now.date()
    else:
        for i, d in enumerate(_DAYS):
            if re.search(rf"\b{d}\b", t):
                ahead = (i - now.weekday()) % 7
                if ahead == 0 or "next" in t:
                    ahead = ahead or 7
                    if "next" in t and ahead < 7 and (i - now.weekday()) % 7 != 0:
                        ahead += 7 if ahead <= 0 else 0
                day = now.date() + dt.timedelta(days=ahead)
                break
    if day is None and clock is None:
        return None
    if clock is None:
        clock = (9, 0)
    if day is None:
        cand = dt.datetime.combine(now.date(), dt.time(*clock))
        return cand if cand > now else cand + dt.timedelta(days=1)
    return dt.datetime.combine(day, dt.time(*clock))


def fuzzy_pick(query: str, choices, cutoff: float = 0.62):
    """Best match of `query` among `choices` (strings), or None. Exact and substring
    matches beat fuzzy ones."""
    q = (query or "").strip().lower()
    if not q:
        return None
    items = list(choices)
    low = {c.lower(): c for c in items}
    if q in low:
        return low[q]
    sub = [c for c in items if q in c.lower()]
    if sub:
        return min(sub, key=len)
    words = [c for c in items if any(w == q for w in re.split(r"\W+", c.lower()))]
    if words:
        return min(words, key=len)
    best = difflib.get_close_matches(q, list(low), n=1, cutoff=cutoff)
    return low[best[0]] if best else None
