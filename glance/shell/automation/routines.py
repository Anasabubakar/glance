"""
routines.py — your own automations: named sequences of commands that run by voice, on a
schedule, or after a delay. Everything a routine does goes through the same fast
automation rules, so routines run instantly and never need an AI.

    "create a routine called morning that opens gmail, opens calendar and sets the volume to 30"
    "when I say start work open vs code and open the terminal"
    "every weekday at 9am run my morning routine"
    "remind me in 20 minutes to stretch"
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import scheduler
from .nlp import parse_duration, parse_when
from .registry import Result, clean, handle, rule, split_compound

FILE = Path.home() / ".glance" / "routines.json"


def load() -> list:
    try:
        return json.loads(FILE.read_text()).get("routines", [])
    except (OSError, ValueError):
        return []


def save(rs: list) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps({"routines": rs}, indent=1))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", (s or "").lower()).strip()


def find(name: str):
    n = _norm(name)
    for r in load():
        if _norm(r["name"]) == n or n in [_norm(p) for p in r.get("phrases", [])]:
            return r
    return None


def upsert(name: str, steps: list, phrases=None, schedule=None) -> dict:
    rs = load()
    r = find(name) or {"name": name.strip(), "phrases": [], "steps": [], "schedule": None, "enabled": True}
    r["steps"] = steps
    if phrases:
        r["phrases"] = sorted(set(r.get("phrases", [])) | {p.strip() for p in phrases})
    if schedule is not None:
        r["schedule"] = schedule
    rs = [x for x in rs if _norm(x["name"]) != _norm(r["name"])] + [r]
    save(rs)
    return r


def remove(name: str) -> bool:
    n = _norm(name)
    rs = load()
    new = [r for r in rs if _norm(r["name"]) != n]
    save(new)
    return len(new) != len(rs)


def run_steps(ctx, steps: list) -> Result:
    said = []
    for step in steps:
        r = handle(ctx, step)
        if r is None:
            return Result(f"I couldn't do: {step}.", ok=False)
        if r.say:
            said.append(r.say)
        time.sleep(0.25)
    return Result(" ".join(said[-1:]) or "Done.")


def run(ctx, name: str) -> Result:
    r = find(name)
    if not r:
        return Result(f"I don't have a routine called {name}.", ok=False)
    ctx.caption(f"Running {r['name']}", 0.5)
    res = run_steps(ctx, r["steps"])
    return Result(res.say if not res.ok else f"Finished {r['name']}.", ok=res.ok)


_THIRD = {"opens": "open", "closes": "close", "sets": "set", "plays": "play", "pauses": "pause", "mutes": "mute",
          "turns": "turn", "types": "type", "presses": "press", "goes": "go", "searches": "search",
          "launches": "launch", "starts": "start", "tiles": "tile", "moves": "move", "minimizes": "minimize",
          "minimises": "minimize", "maximizes": "maximize", "maximises": "maximize", "switches": "switch",
          "takes": "take", "shows": "show", "locks": "lock", "runs": "run", "unmutes": "unmute"}


def _imperative(step: str) -> str:
    w = step.split(" ", 1)
    return (_THIRD.get(w[0].lower(), w[0]) + (" " + w[1] if len(w) > 1 else "")).strip()


def split_steps(text: str) -> list:
    """'open gmail, open calendar and set the volume to 30' -> three commands."""
    parts = [p.strip() for p in re.split(r"\s*(?:,\s*(?:and\s+|then\s+)?|\s+and then\s+|\s+then\s+|\s+and\s+(?=(?:open|close|set|turn|play|pause|mute|type|press|go|search|volume|launch|start|tile|move|minimi[sz]e|maximi[sz]e|switch|take|show|lock|run|unmute)(?:s|es)?\b))", text) if p.strip()]
    return [_imperative(p) for p in (parts or [text.strip()])]


# ── rules ────────────────────────────────────────────────────────────────
def _dry_phrase(text: str) -> bool:
    key = _norm(text)
    return any(r.get("enabled", True) and key in [_norm(p) for p in r.get("phrases", [])] for r in load())


@rule(r".+", name="routine_phrase", prio=1, dry=_dry_phrase)
def routine_phrase(ctx, m, text):
    """A phrase you taught Glance ('start work') or a routine's own name runs it."""
    key = _norm(text)
    for r in load():
        if r.get("enabled", True) and (key in [_norm(p) for p in r.get("phrases", [])]):
            return run(ctx, r["name"])
    return None


@rule(r"(?:run|start|do|play|trigger|launch|execute)\s+(?:my\s+|the\s+)?(?P<n>[\w ]{2,40}?)\s+(?:routine|automation|workflow|shortcut)$", name="run_routine", prio=2)
def run_routine(ctx, m, text):
    return run(ctx, m.group("n"))


@rule(r"(?:create|make|save|add|set up|new)\s+(?:a\s+|an\s+)?(?:new\s+)?(?:routine|automation|workflow)\s+(?:called|named)\s+(?P<n>[\w ]{2,40}?)\s*(?:that|which|to|:|,|-)?\s*(?:does|do|will|should|runs)?\s*(?P<s>(?:open|close|set|turn|play|pause|mute|type|press|go|search|volume|launch|start|tile|move|minimi[sz]e|maximi[sz]e|switch|take|show|lock|play).+)$",
      name="create_routine", prio=3)
def create_routine(ctx, m, text):
    steps = split_steps(m.group("s"))
    bad = [s for s in steps if handle_dry(s) is False]
    if bad:
        return Result(f"I don't know how to do: {bad[0]}.", ok=False)
    r = upsert(m.group("n").strip(), steps)
    return Result(f"Saved the routine {r['name']} with {len(steps)} step{'s' if len(steps) != 1 else ''}. Say run {r['name']} routine.")


_VERBS = r"(?:open|close|set|turn|play|pause|mute|type|press|go|search|volume|launch|start|tile|move|minimi[sz]e|maximi[sz]e|switch|take|show|lock)"


@rule(r"when i say\s+(?P<rest>.+)$", name="when_i_say", prio=3, numbers=False)
def when_i_say(ctx, m, text):
    rest = m.group("rest").strip()
    sep = re.search(r"\s*(?:,|:|\bthen\b)\s*(?=" + _VERBS + r"\b)", rest)
    if sep:
        phrase, steps_text = rest[:sep.start()], rest[sep.end():]
    else:                                   # no separator: the steps start at the first command word
        v = re.search(r"\s(?=" + _VERBS + r"\b)", rest)
        if not v:
            return None
        phrase, steps_text = rest[:v.start()], rest[v.end():]
    phrase = phrase.strip().strip('"\'')
    if not phrase:
        return None
    steps = split_steps(steps_text)
    bad = [s for s in steps if handle_dry(s) is False]
    if bad:
        return Result(f"I don't know how to do: {bad[0]}.", ok=False)
    upsert(phrase, steps, phrases=[phrase])
    return Result(f"Okay. When you say {phrase}, I'll do that.")


@rule(r"(?:delete|remove|forget|cancel)\s+(?:my\s+|the\s+)?(?P<n>[\w ]{2,40}?)\s+(?:routine|automation|workflow)$", name="delete_routine", prio=3)
def delete_routine(ctx, m, text):
    if remove(m.group("n")):
        return Result(f"Deleted {m.group('n')}.")
    return Result(f"I don't have {m.group('n')}.", ok=False)


@rule(r"(?:list|show|what are)\s+(?:all\s+)?(?:my\s+)?(?:routines|automations|workflows)$", name="list_routines", prio=3)
def list_routines(ctx, m, text):
    ns = [r["name"] for r in load()]
    return Result("Your routines: " + ", ".join(ns) + "." if ns else "You don't have any routines yet.")


def handle_dry(step: str):
    """True if some rule understands `step` (without doing it)."""
    from .registry import _understood
    return _understood(clean(step))


# ── timers, reminders, alarms, schedules ─────────────────────────────────
@rule(r"(?:set\s+)?(?:a\s+|an\s+)?(?:timer|countdown)\s+(?:for\s+)?(?P<d>.+)$|(?:wake me|alert me|tell me|ping me|notify me)\s+(?:in|after)\s+(?P<d2>.+)$|start a (?P<d3>.+?)\s+timer$",
      name="timer", prio=5)
def timer(ctx, m, text):
    secs = parse_duration(m.group("d") or m.group("d2") or m.group("d3") or "")
    if not secs:
        return None
    scheduler.add(time.time() + secs, "say", "Your timer is done.")
    mins = secs / 60
    spoken = f"{secs} seconds" if secs < 90 else f"{mins:g} minutes" if secs < 7200 else f"{secs / 3600:g} hours"
    return Result(f"Timer set for {spoken}.")


@rule(r"remind me\s+(?P<w>(?:in|after)\s+.+?|(?:at|tomorrow|tonight|today|next|on)\s+.+?)\s+(?:to|that|about)\s+(?P<t>.+)$|"
      r"remind me\s+(?:to|that|about)\s+(?P<t2>.+?)\s+(?P<w2>(?:in|after)\s+.+|(?:at|tomorrow|tonight|today|next|on)\s+.+)$", name="reminder", prio=5, numbers=True)
def reminder(ctx, m, text):
    what = (m.group("t") or m.group("t2")).strip()
    when = parse_when(m.group("w") or m.group("w2"))
    if not when:
        return None
    scheduler.add(when.timestamp(), "say", f"Reminder: {what}")
    import datetime as _dt
    day = "" if when.date() == _dt.date.today() else f" on {when.strftime('%A')}"
    return Result(f"I'll remind you to {what} at {when.strftime('%I:%M %p').lstrip('0')}{day}.")


@rule(r"(?:set\s+)?(?:an?\s+)?(?:alarm)\s+(?:for\s+|at\s+)?(?P<w>.+)$|wake me up\s+(?:at|tomorrow at)\s+(?P<w2>.+)$", name="alarm", prio=5)
def alarm(ctx, m, text):
    when = parse_when("at " + (m.group("w") or m.group("w2")) if not re.search(r"\b(?:at|tomorrow|today|next|in)\b", m.group("w") or m.group("w2")) else (m.group("w") or m.group("w2")))
    if not when:
        return None
    scheduler.add(when.timestamp(), "say", "Time to wake up. Your alarm is going off.")
    return Result(f"Alarm set for {when.strftime('%I:%M %p').lstrip('0')}.")


@rule(r"(?:cancel|clear|delete|stop)\s+(?:all\s+)?(?:my\s+)?(?:timers|reminders|alarms|scheduled\s+\w+)$", name="cancel_timers", prio=5)
def cancel_timers(ctx, m, text):
    n = 0
    for j in scheduler.jobs():
        if j["kind"] == "say" and scheduler.remove(j["id"]):
            n += 1
    return Result(f"Cancelled {n}.")


@rule(r"(?:every|each)\s+(?P<d>day|weekday|weekdays|morning|evening|night|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:at\s+)?(?P<t>\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight)\s*(?:,|then)?\s*(?P<s>.+)$",
      name="schedule_daily", prio=4)
def schedule_daily(ctx, m, text):
    when = parse_when("at " + m.group("t"))
    if not when:
        return None
    steps = split_steps(re.sub(r"^(?:run|do|start)\s+(?:my\s+)?", "run my ", m.group("s")))
    if any(handle_dry(s) is False for s in steps):
        return Result(f"I don't know how to do: {m.group('s')}.", ok=False)
    rep = "weekdays" if m.group("d") in ("weekday", "weekdays") else "daily"
    scheduler.add(when.timestamp(), "steps", json.dumps(steps), rep)
    return Result(f"Okay. I'll do that every {m.group('d')} at {when.strftime('%I:%M %p').lstrip('0')}.")


@rule(r"(?P<w>(?:in|after)\s+\d+\s*(?:seconds?|minutes?|mins?|hours?)|at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow at\s+\S+(?:\s*(?:am|pm))?)\s*,?\s*(?P<s>(?:open|close|set|turn|play|pause|mute|type|press|go|search|volume|launch|start|tile|move|minimi[sz]e|maximi[sz]e|switch|take|show|lock|run).+)$",
      name="schedule_once", prio=4)
def schedule_once(ctx, m, text):
    when = parse_when(m.group("w"))
    if not when:
        return None
    steps = split_steps(m.group("s"))
    if any(handle_dry(s) is False for s in steps):
        return None
    scheduler.add(when.timestamp(), "steps", json.dumps(steps))
    return Result(f"Okay. I'll do that at {when.strftime('%I:%M %p').lstrip('0')}.")


def fire(ctx_factory, say):
    """Return the scheduler handler. ctx_factory() builds a Ctx; say(msg) speaks on the app's loop."""
    def handler(job):
        if job["kind"] == "say":
            ctx = ctx_factory()
            ctx.notify(job["text"])
            say(job["text"])
        elif job["kind"] == "steps":
            res = run_steps(ctx_factory(), json.loads(job["text"]))
            if res.say:
                say(res.say)
        elif job["kind"] == "routine":
            res = run(ctx_factory(), job["text"])
            if res.say:
                say(res.say)
    return handler
