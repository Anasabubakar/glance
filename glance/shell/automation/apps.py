"""apps.py — open, close and switch apps by their real names (from the installed .desktop files)."""

from __future__ import annotations

import glob
import os
import re
import time

from .nlp import fuzzy_pick
from .registry import Result, rule

_DIRS = ["/usr/share/applications", "/usr/local/share/applications",
         os.path.expanduser("~/.local/share/applications"),
         "/var/lib/flatpak/exports/share/applications",
         os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
         "/var/lib/snapd/desktop/applications"]

ALIASES = {
    "notepad": "text editor", "editor": "text editor", "word": "writer", "word processor": "writer",
    "excel": "calc", "spreadsheet": "calc", "powerpoint": "impress", "presentation": "impress",
    "paint": "drawing", "camera": "cheese", "music": "rhythmbox", "settings": "settings",
    "files": "files", "file manager": "files", "explorer": "files", "task manager": "system monitor",
    "terminal": "terminal", "command line": "terminal", "console": "terminal", "shell": "terminal",
    "calculator": "calculator", "calendar": "calendar", "maps": "maps", "photos": "image viewer",
    "pdf": "document viewer", "pdf viewer": "document viewer", "vs code": "visual studio code",
    "vscode": "visual studio code", "code": "visual studio code", "chrome": "google chrome",
    "google": "google chrome", "internet": "web", "browser": "web", "web browser": "web",
}

_cache = {"t": 0.0, "apps": []}


def index() -> list:
    """[{id, name, keywords, wmclass, exec}] for every launchable app (cached for a minute)."""
    if time.monotonic() - _cache["t"] < 60 and _cache["apps"]:
        return _cache["apps"]
    apps, seen = [], set()
    for d in _DIRS:
        for f in glob.glob(os.path.join(d, "*.desktop")):
            try:
                txt = open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            sec = txt.split("[Desktop Action", 1)[0]
            if "NoDisplay=true" in sec or "Hidden=true" in sec or "Type=Application" not in sec:
                continue
            g = lambda k: (re.search(rf"^{k}=(.*)$", sec, re.M) or [None, ""])[1].strip()  # noqa: E731
            name = g("Name")
            if not name:
                continue
            aid = os.path.basename(f)
            if aid in seen:
                continue
            seen.add(aid)
            apps.append({"id": aid, "name": name, "keywords": g("Keywords").lower(),
                         "wmclass": g("StartupWMClass").lower(), "exec": g("Exec"),
                         "generic": g("GenericName").lower()})
    _cache.update(t=time.monotonic(), apps=apps)
    return apps


def find(query: str):
    """The installed app that best matches what the user said, or None."""
    q = (query or "").strip().lower()
    q = ALIASES.get(q, q)
    apps = index()
    if q == "web":
        for a in apps:
            if "web browser" in a["generic"] or "browser" in a["keywords"]:
                return a
    by_name = {a["name"].lower(): a for a in apps}
    hit = fuzzy_pick(q, by_name, cutoff=0.7)
    if hit:
        return by_name[hit]
    for a in apps:                                    # keywords / generic name / window class
        if q and (q in a["keywords"].split(";") or q == a["generic"] or q == a["wmclass"]
                  or q == a["id"].replace(".desktop", "").split(".")[-1].lower()):
            return a
    return None


def launch(ctx, query: str):
    a = find(query)
    if a:
        return ctx.spawn(["gtk-launch", a["id"]]) and a["name"]
    return None


_NOT_AN_APP = re.compile(r"\b(folder|directory|file|download|link|site|website|page|tab|window|"
                         r"document|picture|photo|video|something|anything|it|this|that|my\s+\w+\s+folder)\b")


@rule(r"(?:open|launch|start|run|fire up|bring up|pull up)\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<a>[\w .+\-']{2,32}?)"
      r"(?:\s+(?:app|application|program))?$", name="open_app", prio=80)
def open_app(ctx, m, text):
    q = m.group("a").strip()
    if _NOT_AN_APP.search(q) or q in ("it", "this", "that") or re.search(r"\b(?:and|then|after|before|while)\b", q):
        return None
    ctx.caption(f"Opening {q}", 0.4)
    if ctx.launch(q):                               # the manager's launcher table and web apps
        return Result(f"Opening {q}.")
    name = launch(ctx, q)
    if name:
        return Result(f"Opening {name}.")
    return None


@rule(r"(?:close|quit|exit|kill|shut down|shutdown|stop)\s+(?:all\s+)?(?:the\s+|my\s+)?(?P<a>[\w .+\-']{2,32}?)"
      r"(?:\s+(?:app|application|program|windows?))?$", name="close_app", prio=60)
def close_app(ctx, m, text):
    q = m.group("a").strip()
    if q in ("it", "this", "that", "window", "tab", "this window", "everything", "all", "the window"):
        return None
    wins = ctx.windows()
    if not wins:
        return None
    from .windows import match_windows
    hit = match_windows(wins, q)
    if not hit:
        return Result(f"I don't see {q} open.", ok=False)
    if re.search(r"\ball\b", text):
        for w in hit:
            ctx.window_action(str(w["id"]), "close")
        return Result(f"Closed all {q} windows.")
    ctx.window_action(str(hit[-1]["id"]), "close")      # just the top one; "close all X" closes every one
    return Result(f"Closed {q}.")


@rule(r"(?:switch to|go to|focus(?: on)?|bring up|alt tab to|jump to|show me)\s+(?:the\s+|my\s+)?(?P<a>[\w .+\-']{2,32}?)"
      r"(?:\s+(?:window|app))?$", name="switch_app", prio=65)
def switch_app(ctx, m, text):
    q = m.group("a").strip()
    if re.search(r"\.(com|org|net|io|dev|app)\b", q) or q in ("it", "this", "that", "desktop", "home", "workspace"):
        return None
    if re.match(r"(?:tab|page|line|top|bottom|the top|the bottom|workspace|desktop|next|previous|last)\b", q):
        return None
    if re.match(r"(?:workspace|desktop)\s*\d+|(?:next|previous|last|another)", q):
        return None
    wins = ctx.windows()
    from .windows import match_windows
    hit = match_windows(wins, q) if wins else []
    if hit:
        ctx.window_action(str(hit[-1]["id"]), "activate")
        return Result(f"Switched to {q}.")
    if wins and ctx.launch(q):
        return Result(f"Opening {q}.")
    return None
