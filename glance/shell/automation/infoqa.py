"""infoqa.py — instant answers computed locally: time, battery, disk, math, units, clipboard, dice."""

from __future__ import annotations

import ast
import datetime as dt
import math
import operator
import os
import random
import re
import shutil
import socket

from .nlp import parse_when
from .registry import Result, rule


def _fmt_time(now: dt.datetime) -> str:
    return now.strftime("It's %I:%M %p.").replace(" 0", " ", 1).replace("It's 0", "It's ")


@rule(r"what(?:'s| is)?\s+(?:the\s+)?(?:current\s+)?time(?:\s+(?:is it|now|right now))?$|what time is it(?:\s+now)?$|tell me the time$|current time$|time$",
      name="time", prio=15)
def time_now(ctx, m, text):
    return Result(_fmt_time(dt.datetime.now()))


@rule(r"what(?:'s| is)?\s+(?:the\s+|today's\s+)?(?:date|day)(?:\s+(?:today|is it|it is))?$|what day is it(?:\s+today)?$|today's date$|what's today$", name="date", prio=15)
def date_now(ctx, m, text):
    return Result(dt.datetime.now().strftime("It's %A, %B %d, %Y.").replace(" 0", " "))


@rule(r"(?:how many days|how long|how many weeks|how much time)\s+(?:until|till|to|before)\s+(?P<w>.+)$|days until\s+(?P<w2>.+)$", name="days_until", prio=16)
def days_until(ctx, m, text):
    w = (m.group("w") or m.group("w2")).strip()
    now = dt.datetime.now()
    known = {"christmas": (12, 25), "new year": (1, 1), "new year's": (1, 1), "new years": (1, 1), "halloween": (10, 31),
             "valentine's day": (2, 14), "valentines day": (2, 14), "independence day": (7, 4)}
    target = None
    for k, (mo, d) in known.items():
        if k in w:
            target = dt.datetime(now.year, mo, d)
            if target < now:
                target = dt.datetime(now.year + 1, mo, d)
    if target is None:
        target = parse_when(w, now)
    if target is None:
        return None
    days = (target.date() - now.date()).days
    return Result(f"{days} day{'s' if days != 1 else ''}.")


@rule(r"(?:what(?:'s| is)\s+)?(?:my\s+|the\s+)?battery(?:\s+(?:level|percentage|status|left|life))?$|how much battery(?: do i have)?(?: left)?$|battery (?:level|status)$",
      name="battery", prio=15)
def battery(ctx, m, text):
    try:
        base = "/sys/class/power_supply"
        bats = [d for d in os.listdir(base) if d.startswith("BAT")]
        cap = int(open(f"{base}/{bats[0]}/capacity").read().strip())
        status = open(f"{base}/{bats[0]}/status").read().strip().lower()
        return Result(f"Battery is at {cap} percent and {status}.")
    except Exception:
        return Result("I can't read a battery on this computer.", ok=False)


@rule(r"(?:how much\s+)?(?:disk|storage|drive)\s+space(?:\s+(?:do i have|is left|left|available|free))?$|how much (?:storage|space) (?:do i have |is )?(?:left|free|available)$|disk (?:usage|space)$",
      name="disk", prio=15)
def disk(ctx, m, text):
    u = shutil.disk_usage(str(ctx.home))
    gb = lambda n: f"{n / 1e9:.0f}"  # noqa: E731
    return Result(f"{gb(u.free)} gigabytes free out of {gb(u.total)}.")


@rule(r"(?:how much\s+)?(?:ram|memory)(?:\s+(?:am i using|is (?:used|free)|do i have|usage|left))?$|memory usage$", name="memory", prio=15)
def memory(ctx, m, text):
    try:
        info = {k: int(v.split()[0]) for k, v in (ln.split(":", 1) for ln in open("/proc/meminfo"))}
        total, avail = info["MemTotal"] / 1e6, info["MemAvailable"] / 1e6
        return Result(f"{avail:.1f} gigabytes free out of {total:.1f}.")
    except Exception:
        return None


@rule(r"(?:what(?:'s| is)\s+)?(?:the\s+|my\s+)?(?:cpu|processor)(?:\s+(?:usage|load))?$|how busy is (?:my|the) (?:computer|cpu)$|system load$", name="cpu", prio=15)
def cpu(ctx, m, text):
    one, _five, _fifteen = os.getloadavg()
    cores = os.cpu_count() or 1
    return Result(f"Load is {one:.1f} on {cores} cores, about {min(100, one / cores * 100):.0f} percent busy.")


@rule(r"(?:how long|what(?:'s| is)(?: my| the)?)\s+(?:has\s+)?(?:the\s+|my\s+)?(?:computer\s+|laptop\s+)?(?:been\s+)?(?:up|on|running)(?:time)?$|uptime$", name="uptime", prio=15)
def uptime(ctx, m, text):
    try:
        s = float(open("/proc/uptime").read().split()[0])
        h, mi = int(s // 3600), int(s % 3600 // 60)
        return Result(f"Up for {h} hour{'s' if h != 1 else ''} and {mi} minute{'s' if mi != 1 else ''}.")
    except Exception:
        return None


@rule(r"(?:what(?:'s| is)\s+)?(?:my\s+)?(?:local\s+)?ip(?:\s+address)?$", name="ip", prio=15)
def ip(ctx, m, text):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        addr = s.getsockname()[0]
        s.close()
        return Result(f"Your local address is {addr.replace('.', ' dot ')}.")
    except Exception:
        return Result("I'm not connected to a network.", ok=False)


@rule(r"(?:what(?:'s| is)\s+)?(?:the\s+|my\s+)?(?:wi-?fi|network)(?:\s+(?:name|i'm on|am i on|connected to))?$|which wi-?fi (?:am i on|is this)$|what wi-?fi am i (?:on|connected to)$",
      name="wifi_name", prio=15)
def wifi_name(ctx, m, text):
    rc, out = ctx.run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], timeout=4)
    for ln in out.splitlines():
        if ln.startswith("yes:"):
            return Result(f"You're on {ln[4:]}.")
    return Result("You're not on Wi-Fi.", ok=False)


# ── math ──────────────────────────────────────────────────────────────────
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg,
        ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log10,
          "ln": math.log, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil}


def safe_eval(expr: str):
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 1000:
                raise ValueError("too big")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and len(n.args) == 1:
            return _FUNCS[n.func.id](ev(n.args[0]))
        if isinstance(n, ast.Name) and n.id in ("pi", "e"):
            return math.pi if n.id == "pi" else math.e
        raise ValueError("unsupported")
    return ev(ast.parse(expr, mode="eval").body)


def _speak_number(v) -> str:
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.6g}" if abs(v) < 1e6 else f"{v:.6g}"
    return str(v)


def _words_to_expr(t: str) -> str:
    t = t.lower()
    for a, b in ((r"\bplus\b", "+"), (r"\bminus\b", "-"), (r"\b(?:times|multiplied by|x)\b", "*"),
                 (r"\b(?:divided by|over)\b", "/"), (r"\bto the power of\b", "**"), (r"\bsquared\b", "**2"),
                 (r"\bcubed\b", "**3"), (r"\bmod(?:ulo)?\b", "%"), (r"\bsquare root of\s+([\d.]+)", r"sqrt(\1)"),
                 (r"\bpoint\b", "."), (r"[,$]", ""), (r"\^", "**"), (r"(\d)\s*x\s*(\d)", r"\1*\2")):
        t = re.sub(a, b, t)
    return t


@rule(r"(?:what(?:'s| is)|calculate|compute|how much is|whats|solve|work out|evaluate)\s+(?P<e>[\d\s+\-*/().,%^x$]+|[\w\s+\-*/().,%^$]*\d[\w\s+\-*/().,%^$]*)$|(?P<e2>[\d.]+\s*[+\-*/x×÷^]\s*[\d.\s+\-*/x×÷^()]+)$",
      name="math", prio=17)
def math_q(ctx, m, text):
    raw = (m.group("e") or m.group("e2") or "").replace("×", "*").replace("÷", "/")
    mp = re.match(r"\s*([\d.]+)\s*(?:%|percent)\s+of\s+([\d.,]+)\s*$", raw)
    if mp:
        v = float(mp.group(1)) / 100 * float(mp.group(2).replace(",", ""))
        return Result(f"{_speak_number(round(v, 6))}.")
    expr = _words_to_expr(raw).strip()
    if not re.fullmatch(r"[\d\s+\-*/().%]*(?:sqrt\([\d.]+\))?[\d\s+\-*/().%]*", expr) or not re.search(r"\d", expr):
        return None
    try:
        v = safe_eval(expr)
    except Exception:
        return None
    return Result(f"{_speak_number(v)}.")


@rule(r"(?:what(?:'s| is)\s+)?(?P<p>[\d.]+)\s*(?:%|percent)\s+of\s+(?P<n>[\d.,]+)$", name="percent_of", prio=17)
def percent_of(ctx, m, text):
    v = float(m.group("p")) / 100 * float(m.group("n").replace(",", ""))
    return Result(f"{_speak_number(round(v, 6))}.")


@rule(r"(?:what(?:'s| is)\s+)?(?:the\s+)?square root of\s+(?P<n>[\d.]+)$|sqrt of (?P<n2>[\d.]+)$", name="sqrt", prio=17)
def sqrt_q(ctx, m, text):
    v = math.sqrt(float(m.group("n") or m.group("n2")))
    return Result(f"{_speak_number(round(v, 6))}.")


@rule(r"(?:what(?:'s| is)\s+)?(?:the\s+)?tip\s+(?:on|for)\s+\$?(?P<b>[\d.]+)\s*(?:at|with)\s+(?P<p>[\d.]+)\s*(?:%|percent)$", name="tip", prio=17)
def tip(ctx, m, text):
    b, p = float(m.group("b")), float(m.group("p"))
    t = b * p / 100
    return Result(f"The tip is {t:.2f}, so the total is {b + t:.2f}.")


# ── unit conversion ───────────────────────────────────────────────────────
_LEN = {"mm": 0.001, "millimeter": 0.001, "millimeters": 0.001, "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
        "m": 1, "meter": 1, "meters": 1, "metre": 1, "metres": 1, "km": 1000, "kilometer": 1000, "kilometers": 1000,
        "kilometre": 1000, "kilometres": 1000, "inch": 0.0254, "inches": 0.0254, "in": 0.0254, "foot": 0.3048, "feet": 0.3048,
        "ft": 0.3048, "yard": 0.9144, "yards": 0.9144, "mile": 1609.344, "miles": 1609.344, "mi": 1609.344}
_MASS = {"mg": 1e-6, "g": 0.001, "gram": 0.001, "grams": 0.001, "kg": 1, "kilogram": 1, "kilograms": 1, "kilo": 1, "kilos": 1,
         "ounce": 0.0283495, "ounces": 0.0283495, "oz": 0.0283495, "pound": 0.453592, "pounds": 0.453592, "lb": 0.453592,
         "lbs": 0.453592, "ton": 1000, "tons": 1000, "tonne": 1000, "stone": 6.35029}
_VOL = {"ml": 0.001, "milliliter": 0.001, "milliliters": 0.001, "l": 1, "liter": 1, "liters": 1, "litre": 1, "litres": 1,
        "gallon": 3.78541, "gallons": 3.78541, "quart": 0.946353, "quarts": 0.946353, "pint": 0.473176, "pints": 0.473176,
        "cup": 0.236588, "cups": 0.236588, "tablespoon": 0.0147868, "tablespoons": 0.0147868, "tbsp": 0.0147868,
        "teaspoon": 0.00492892, "teaspoons": 0.00492892, "tsp": 0.00492892, "fl oz": 0.0295735}
_TIME = {"second": 1, "seconds": 1, "sec": 1, "minute": 60, "minutes": 60, "min": 60, "hour": 3600, "hours": 3600,
         "day": 86400, "days": 86400, "week": 604800, "weeks": 604800, "year": 31557600, "years": 31557600}
_DATA = {"byte": 1, "bytes": 1, "kb": 1024, "kilobyte": 1024, "kilobytes": 1024, "mb": 1024 ** 2, "megabyte": 1024 ** 2,
         "megabytes": 1024 ** 2, "gb": 1024 ** 3, "gigabyte": 1024 ** 3, "gigabytes": 1024 ** 3, "tb": 1024 ** 4, "terabyte": 1024 ** 4}
_SPEED = {"mph": 0.44704, "kph": 0.277778, "km/h": 0.277778, "kmh": 0.277778, "m/s": 1, "knots": 0.514444, "knot": 0.514444}
_TABLES = [_LEN, _MASS, _VOL, _TIME, _DATA, _SPEED]
_TEMP = {"celsius", "fahrenheit", "kelvin", "c", "f", "k"}


def convert(value: float, a: str, b: str):
    a, b = a.lower().strip(), b.lower().strip()
    if a in _TEMP and b in _TEMP:
        a, b = a[0], b[0]
        c = value if a == "c" else (value - 32) * 5 / 9 if a == "f" else value - 273.15
        return c if b == "c" else c * 9 / 5 + 32 if b == "f" else c + 273.15
    for t in _TABLES:
        if a in t and b in t:
            return value * t[a] / t[b]
    return None


_UN = r"(?:fl oz|[a-z/]{1,16})"


@rule(rf"(?:convert\s+)?(?P<v>-?[\d.,]+)\s*(?:degrees?\s+)?(?P<a>{_UN})\s+(?:to|in|into|as)\s+(?:degrees?\s+)?(?P<b>{_UN})$|"
      rf"how many\s+(?P<b2>{_UN})\s+(?:are\s+)?(?:in|are in)\s+(?:a|an|one|1|(?P<v2>[\d.,]+))\s*(?P<a2>{_UN})$", name="convert", prio=18)
def convert_q(ctx, m, text):
    if m.group("v") is not None:
        v, a, b = float(m.group("v").replace(",", "")), m.group("a"), m.group("b")
    else:
        v, a, b = float((m.group("v2") or "1").replace(",", "")), m.group("a2"), m.group("b2")
    r = convert(v, a, b)
    if r is None:
        return None
    return Result(f"{_speak_number(round(v, 6))} {a} is about {_speak_number(round(r, 4))} {b}.")


# ── randomness and text ───────────────────────────────────────────────────
@rule(r"flip a coin$|toss a coin$|heads or tails$", name="coin", prio=19)
def coin(ctx, m, text):
    return Result(random.choice(["Heads.", "Tails."]))


@rule(r"roll (?:a\s+|an\s+)?(?:die|dice|d(?P<s>\d+))$|roll (?:a )?(?P<n>\d+)?\s*sided die$", name="dice", prio=19)
def dice(ctx, m, text):
    sides = int(m.group("s") or m.group("n") or 6)
    return Result(f"You rolled a {random.randint(1, max(2, sides))}.")


@rule(r"(?:pick|give me|choose|generate|say)\s+(?:a\s+)?(?:random\s+)?number\s+(?:between|from)\s+(?P<a>\d+)\s+(?:and|to)\s+(?P<b>\d+)$|random number$",
      name="random_number", prio=19)
def random_number(ctx, m, text):
    a, b = int(m.group("a") or 1), int(m.group("b") or 100)
    return Result(f"{random.randint(min(a, b), max(a, b))}.")


@rule(r"(?:pick|choose)\s+(?:one\s+)?(?:from|between|of)\s+(?P<o>.+?\s+(?:or|,)\s+.+)$", name="choose", prio=19)
def choose(ctx, m, text):
    opts = [o.strip() for o in re.split(r"\s*(?:,|\bor\b)\s*", m.group("o")) if o.strip()]
    if len(opts) < 2:
        return None
    return Result(f"{random.choice(opts)}.")


@rule(r"(?:what(?:'s| is)\s+)?(?:on\s+)?(?:my\s+)?clipboard$|(?:read|say|show)\s+(?:me\s+)?(?:my\s+|the\s+)?clipboard(?:\s+(?:aloud|out loud))?$|what did i (?:just\s+)?copy$",
      name="read_clipboard", prio=14)
def read_clipboard(ctx, m, text):
    t = ctx.clipboard_get("clipboard").strip()
    if not t:
        return Result("Your clipboard is empty.", ok=False)
    return Result(t[:400] + ("…" if len(t) > 400 else ""))


@rule(r"(?:read|say)\s+(?:the\s+)?(?:selected|highlighted)\s+(?:text|words)(?:\s+(?:aloud|out loud))?$|read (?:this|that)(?: aloud| out loud)$|read (?:it )?aloud$",
      name="read_selection", prio=14)
def read_selection(ctx, m, text):
    t = ctx.clipboard_get("primary").strip()
    if not t:
        return Result("Nothing is selected.", ok=False)
    return Result(t[:600] + ("…" if len(t) > 600 else ""))


@rule(r"(?:clear|empty)\s+(?:my\s+|the\s+)?clipboard$", name="clear_clipboard", prio=14)
def clear_clipboard(ctx, m, text):
    ctx.clipboard_set("")
    return Result("Cleared the clipboard.")


@rule(r"(?:copy|put)\s+(?P<t>.+?)\s+(?:to|on|in|onto)\s+(?:the\s+|my\s+)?clipboard$", name="copy_text", prio=14, numbers=False)
def copy_text(ctx, m, text):
    ctx.clipboard_set(m.group("t").strip().strip('"\''))
    return Result("Copied.")


@rule(r"how many\s+(?P<w>words|characters|letters)\s+(?:are\s+)?(?:in|on)\s+(?:my\s+|the\s+)?(?:clipboard|selection|selected text)$", name="count_clip", prio=14)
def count_clip(ctx, m, text):
    t = ctx.clipboard_get("primary" if "select" in text else "clipboard")
    if not t.strip():
        return Result("There's nothing there.", ok=False)
    n = len(t.split()) if m.group("w") == "words" else len(re.sub(r"\s", "", t))
    return Result(f"{n} {m.group('w')}.")
