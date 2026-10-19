"""
localcmd.py — instant, offline handling of everyday desktop commands.

"minimize this window", "open the calculator", "volume up", "go back", "what time is
it" never need a language model: understanding them takes microseconds and doing them
through the compositor is exact. Pure parsing lives here (easy to test); the app
executes the returned Command.

parse(text) -> Command | None.  None means "not a simple local command": the request
goes on to the AI as before.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LEAD = re.compile(
    r"^(?:(?:hey|ok|okay)[ ,]+)?(?:glance[ ,]+)?(?:(?:please|can you|could you|would you|will you|"
    r"i want you to|i need you to|go ahead and)[ ,]+)*(?:please[ ,]+)?", re.I)
_TAIL = re.compile(r"[\s.!?]*(?:please|for me|now|thanks|thank you)?[\s.!?]*$", re.I)

_WIN_WORDS = {"minimize": "minimize", "minimise": "minimize", "hide": "minimize",
              "maximize": "maximize", "maximise": "maximize", "restore": "unmaximize",
              "unmaximize": "unmaximize", "close": "close", "fullscreen": "fullscreen",
              "full screen": "fullscreen", "exit": "close", "quit": "close"}
_THIS = r"(?:this|that|the|current|active|open|my)?(?:\s+(?:current|active|open))*"

_KEYS = {
    "go back": "alt+Left", "go forward": "alt+Right", "new tab": "ctrl+t",
    "close tab": "ctrl+w", "close the tab": "ctrl+w", "close this tab": "ctrl+w",
    "refresh": "F5", "reload": "F5", "refresh the page": "F5", "reload the page": "F5",
    "copy": "ctrl+c", "paste": "ctrl+v", "cut": "ctrl+x", "undo": "ctrl+z", "redo": "ctrl+shift+z",
    "select all": "ctrl+a", "save": "ctrl+s", "save it": "ctrl+s", "find": "ctrl+f",
    "next tab": "ctrl+Tab", "previous tab": "ctrl+shift+Tab", "zoom in": "ctrl+plus",
    "zoom out": "ctrl+minus", "scroll to the top": "ctrl+Home", "scroll to the bottom": "ctrl+End",
    "show the desktop": "super+d", "show desktop": "super+d", "open the overview": "super",
}


@dataclass
class Command:
    kind: str                       # window | activate | open_app | url | volume | key | type | scroll | answer | lock
    arg: str = ""                   # window action, app name, url, key combo, text ...
    target: str = ""                # window selector (a name), "" = the focused window
    n: int = 0                      # amount (volume %, scroll notches)
    say: str = ""                   # what to say when done
    extra: dict = field(default_factory=dict)


def _clean(text: str) -> str:
    t = (text or "").strip()
    t = _LEAD.sub("", t)
    t = _TAIL.sub("", t)
    return t.strip()


def _norm_target(t: str) -> str:
    t = re.sub(r"^(?:the|my|this|that|current|active|open)\s+", "", (t or "").strip(), flags=re.I)
    t = re.sub(r"\s+(?:window|app|application|program|tab)$", "", t, flags=re.I)
    return t.strip()


_SOFT = {"it", "this", "that", "window", "this window", "that window", "the window", "everything",
         "current", "active", ""}


def parse(text: str):
    s = _clean(text)
    low = s.lower()
    if not low or len(low.split()) > 12:
        return None
    if re.search(r"\b(and|then|after that|afterwards)\b", low) and not low.startswith(
            ("search ", "go to ", "stop recording", "finish recording", "end recording")):
        return None                     # a multi-step request: let the AI plan it

    # window control: "minimize the terminal window", "close this", "maximize it"
    m = re.match(r"(?P<verb>minimi[sz]e|maximi[sz]e|restore|unmaximi[sz]e|close|hide|full ?screen|exit|quit)"
                 r"(?:\s+(?P<obj>.+))?$", low)
    if m:
        act = _WIN_WORDS.get(m.group("verb").replace(" ", " "), None) or _WIN_WORDS.get(
            m.group("verb").replace("z", "s"), None)
        obj = (m.group("obj") or "").strip()
        if obj in ("tab", "this tab", "the tab", "the current tab", "current tab") and act == "close":
            return Command("key", "ctrl+w", say="Closed the tab.")
        tgt = "" if obj in _SOFT else _norm_target(obj)
        if act and (tgt == "" or len(tgt.split()) <= 3):
            return Command("window", act, target=tgt)
    m = re.match(r"(?:minimi[sz]e|maximi[sz]e|close|hide)\s+it$", low)  # handled above via _SOFT
    # switching: "switch to chrome", "focus the terminal", "bring up files"
    m = re.match(r"(?:switch to|go to|focus(?: on)?|bring up|show me|alt tab to)\s+(?:the\s+)?(?P<t>[\w .-]{2,40}?)"
                 r"(?:\s+window)?$", low)
    if m and not re.search(r"\.(com|org|net|io|dev|app)\b|http", low) and not low.startswith("go to "):
        return Command("activate", target=_norm_target(m.group("t")))

    # volume
    if re.match(r"(?:turn )?(?:the )?(?:volume|sound)\s*(?:up|louder)|turn (?:it )?up|louder|volume up|increase (?:the )?volume", low):
        return Command("volume", "up", n=10, say="Volume up.")
    if re.match(r"(?:turn )?(?:the )?(?:volume|sound)\s*(?:down|lower|quieter)|turn (?:it )?down|quieter|volume down|decrease (?:the )?volume|lower (?:the )?volume", low):
        return Command("volume", "down", n=10, say="Volume down.")
    if re.match(r"(?:un)?mute(?: (?:the )?(?:sound|volume|audio))?$", low):
        return Command("volume", "unmute" if low.startswith("un") else "mute",
                       say="Unmuted." if low.startswith("un") else "Muted.")
    m = re.match(r"(?:set )?(?:the )?volume (?:to|at) (\d{1,3})\s*(?:%|percent)?$", low)
    if m:
        n = max(0, min(100, int(m.group(1))))
        return Command("volume", "set", n=n, say=f"Volume {n} percent.")

    # keyboard shortcuts by name
    if low in _KEYS:
        return Command("key", _KEYS[low], say="Done.")
    m = re.match(r"press\s+(?P<k>[\w+ ]{1,30})$", low)
    if m:
        combo = re.sub(r"\s*\+\s*", "+", m.group("k").strip().replace(" plus ", "+"))
        combo = combo.replace("control", "ctrl").replace("escape", "Escape").replace("enter", "Return")
        return Command("key", combo, say=f"Pressed {m.group('k').strip()}.")
    m = re.match(r"(?:type|write|enter)\s+(?:out\s+)?(?P<t>.+)$", s, re.I)
    if m:
        t = m.group("t").strip()
        quoted = len(t) > 1 and t[0] in "\"“'" and t[-1] in "\"”'"
        vague = re.match(r"(?:something|anything|a |an |some |it\b|that\b|this\b|your |my )", t, re.I)
        place = re.search(r"\b(?:in|into|on|inside|at|to)\s+(?:the|my|this|that|a|an)\b", t, re.I)
        if quoted or (not vague and not place):
            return Command("type", t.strip('"“”\''), say="Typed it.")
        return None                        # "type something in the editor": needs the screen and an AI

    # scrolling
    m = re.match(r"scroll\s+(?P<d>up|down)(?:\s+(?P<a>a (?:little|bit|lot)|a lot|a little|a bit|more|\d+))?$", low)
    if m:
        a = m.group("a") or ""
        n = 12 if "lot" in a else 3 if ("little" in a or "bit" in a) else 6
        return Command("scroll", m.group("d"), n=n, say="")

    # web: "go to youtube.com", "search for cats", "google cats"
    m = re.match(r"(?:go to|open|visit|navigate to)\s+(?P<u>(?:https?://)?[\w-]+(?:\.[\w-]+)+(?:/\S*)?)$", low)
    if m:
        u = m.group("u")
        return Command("url", u if u.startswith("http") else "https://" + u, say="Opening it.")
    m = re.match(r"(?:search(?: the web| google| online)?(?: for)?|google|look up)\s+(?P<q>.+)$", low)
    if m and len(m.group("q").split()) <= 9:
        from urllib.parse import quote_plus
        return Command("url", "https://www.google.com/search?q=" + quote_plus(m.group("q")),
                       say=f"Searching for {m.group('q')}.")

    # drawing a shape in the window you are using: "draw a circle", "sketch a heart"
    m = re.match(r"(?:draw|sketch|doodle|paint|make)\s+(?:me\s+)?(?:a|an|some)?\s*(?P<s>circle|star|heart|square|"
                 r"triangle|spiral|smiley(?: face)?|rectangle|zigzag|wave)s?$", low)
    if m:
        shape = m.group("s").replace(" face", "")
        return Command("draw", shape, say=f"Drawing a {shape}.")

    # macros: record once, replay with no AI
    m = re.match(r"(?:start|begin)\s+(?:recording|capturing)(?:\s+(?:a|my|the))?(?:\s+(?:macro|workflow))?(?:\s+(?:called|named)\s+(?P<n>.+))?$", low)
    if m:
        return Command("macro_start", m.group("n") or "", say="Recording. Do the steps, then say stop recording.")
    m = re.match(r"(?:stop|finish|end)\s+recording(?:\s+(?:and\s+)?(?:save\s+(?:it\s+)?)?(?:as|called|named)\s+(?P<n>.+))?$", low)
    if m:
        return Command("macro_stop", m.group("n") or "")
    m = re.match(r"(?:run|play|replay|do|start)\s+(?:the\s+|my\s+)?(?P<n>[\w ]{1,30}?)\s+(?:macro|workflow)$", low)
    if m:
        return Command("macro_run", m.group("n"))
    if re.match(r"(?:replay|run|play)\s+(?:the\s+)?last\s+(?:macro|workflow|recording)$", low):
        return Command("macro_run", "last")
    if re.match(r"(?:list|show|what are)\s+(?:my\s+)?(?:macros|workflows)$", low):
        return Command("macro_list")

    # timers and reminders
    nums = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ten": 10,
            "fifteen": 15, "twenty": 20, "thirty": 30, "forty five": 45, "sixty": 60}
    unit = r"(?P<u>seconds?|secs?|minutes?|mins?|hours?)"
    num = r"(?P<n>\d+(?:\.\d+)?|a|an|one|two|three|four|five|ten|fifteen|twenty|thirty|forty five|sixty)"

    def _secs(mm):
        v = mm.group("n")
        n = float(v) if v.replace(".", "").isdigit() else nums.get(v, 1)
        u = mm.group("u")
        return int(n * (3600 if u.startswith("h") else 60 if u.startswith("m") else 1))
    m = re.match(rf"remind me (?:in|after) {num}\s*{unit}\s+(?:to|that|about)\s+(?P<t>.+)$", low)
    if m:
        return Command("timer", m.group("t"), n=_secs(m), say=f"Okay, I'll remind you to {m.group('t')}.")
    m = re.match(rf"(?:set\s+)?(?:a\s+)?(?:timer|alarm)\s+(?:for\s+)?{num}\s*{unit}$", low) or \
        re.match(rf"(?:wake me|alert me|tell me)\s+(?:in|after)\s+{num}\s*{unit}$", low)
    if m:
        return Command("timer", "Your timer is done", n=_secs(m), say="Timer set.")

    # media keys (any MPRIS player: Spotify, VLC, browsers, ...)
    if re.match(r"(?:play|pause|resume|stop)(?:\s+(?:the\s+)?(?:music|song|video|media|playback|it))?$", low):
        return Command("media", "PlayPause", say="")
    if re.match(r"(?:next|skip)(?:\s+(?:song|track|video))?$", low):
        return Command("media", "Next", say="")
    if re.match(r"(?:previous|last)\s+(?:song|track|video)$|go to the previous (?:song|track)$", low):
        return Command("media", "Previous", say="")

    # settings you can flip instantly
    m = re.match(r"(?:turn on|enable|switch to|use|go)\s+(?:the\s+)?(?P<t>dark|light)\s*(?:mode|theme)?$", low)
    if m:
        return Command("theme", m.group("t"), say=f"{m.group('t').title()} mode.")
    if re.match(r"(?:what(?:'s| is)|how much is|check)\s+(?:my\s+|the\s+)?battery(?:\s+(?:level|percentage|left))?$|battery (?:level|status)$", low):
        return Command("battery")
    if re.match(r"(?:take|grab|capture)\s+(?:a\s+)?screenshot(?: of (?:my|the) screen)?$|screenshot$", low):
        return Command("screenshot", say="Saved a screenshot.")

    # facts we know instantly
    if re.match(r"what(?:'s| is) the time|what time is it|tell me the time|current time$", low):
        return Command("answer", "time")
    if re.match(r"what(?:'s| is) (?:the )?(?:date|day)(?: today)?|what day is it(?: today)?$", low):
        return Command("answer", "date")
    if re.match(r"lock (?:the |my )?(?:screen|computer|laptop|pc)$", low):
        return Command("lock", say="Locking the screen.")

    # launching an app: "open the calculator", "launch firefox", "start the terminal"
    m = re.match(r"(?:open|launch|start|run|fire up)\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<a>[\w .+-]{2,30}?)"
                 r"(?:\s+(?:app|application|program))?$", low)
    if m:
        a = m.group("a").strip()
        if (not re.search(r"\b(folder|directory|file|link|website|site|page|tab|window)\b", a)
                and a not in ("it", "this", "that", "something", "anything")):
            return Command("open_app", a, say=f"Opening {a}.")
    return None
