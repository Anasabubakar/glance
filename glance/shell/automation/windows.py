"""windows.py — exact window control: minimize, maximize, close, tile, workspaces, always-on-top."""

from __future__ import annotations

import re

from .registry import Result, rule

APP_HINTS = {
    "browser": ("brave", "chrome", "chromium", "firefox", "edge", "vivaldi", "opera", "zen"),
    "web browser": ("brave", "chrome", "chromium", "firefox", "edge"),
    "terminal": ("terminal", "ptyxis", "konsole", "xterm", "kitty", "alacritty"),
    "files": ("nautilus", "files", "dolphin", "nemo", "thunar"),
    "file manager": ("nautilus", "files", "dolphin", "nemo", "thunar"),
    "editor": ("texteditor", "gedit", "kate", "code", "sublime", "text editor"),
    "text editor": ("texteditor", "gedit", "kate", "text editor"),
    "notepad": ("texteditor", "gedit", "kate", "text editor"),
    "code": ("code", "vscode"), "vs code": ("code",), "chrome": ("chrome", "chromium"),
    "calculator": ("calculator",), "settings": ("control-center", "settings"),
    "music": ("rhythmbox", "spotify", "lollypop"), "mail": ("thunderbird", "geary", "evolution"),
}


def match_windows(wins: list, target: str) -> list:
    """Windows whose title/class/app matches `target` (bottom-to-top order)."""
    t = (target or "").lower().strip()
    t = re.sub(r"^(?:the|my)\s+", "", t)
    keys = APP_HINTS.get(t, (t,))
    out = []
    for w in wins:
        hay = f"{w.get('title', '')} {w.get('wm_class', '')} {w.get('app', '')}".lower()
        if any(k in hay for k in keys):
            out.append(w)
    return out


def pick(ctx, target: str):
    wins = [w for w in ctx.windows() if not w.get("glance")]
    if not target:
        return next((w for w in wins if w.get("focused")), None) or (wins[-1] if wins else None)
    hit = match_windows(wins, target)
    return hit[-1] if hit else None


_SOFT = {"it", "this", "that", "window", "this window", "that window", "the window", "current",
         "active", "current window", "active window", ""}


def _target(raw: str) -> str:
    t = (raw or "").strip().lower()
    if t in _SOFT:
        return ""
    t = re.sub(r"^(?:the|my|this|that|current|active|open)\s+", "", t)
    return re.sub(r"\s+(?:window|app|application|program)$", "", t).strip()


_BUTTON = {"minimize": 100, "maximize": 62, "unmaximize": 62, "fullscreen": 62, "close": 26}
_VERB = {"minimize": "Minimizing", "maximize": "Maximizing", "unmaximize": "Restoring",
         "close": "Closing", "fullscreen": "Going full screen"}
_DONE = {"minimize": "Minimized.", "maximize": "Maximized.", "unmaximize": "Restored.",
         "close": "Closed.", "fullscreen": "Full screen."}


def do_window(ctx, w, act: str, label: str = ""):
    title = (w.get("title") or w.get("wm_class") or "the window")[:40]
    x, y = w["x"] + w["w"] - _BUTTON.get(act, 62), w["y"] + 20
    ctx.fly(x, y, label or f"{_VERB.get(act, 'Moving')} {title}", 0.9)
    res = ctx.window_action(str(w["id"]), act)
    ctx.release()
    return bool(res and res.get("ok"))


@rule(r"(?:minimi[sz]e|maximi[sz]e|restore|unmaximi[sz]e|full ?screen|hide)(?:\s+(?P<o>.+))?$", name="window_verb", prio=30)
def window_verb(ctx, m, text):
    verb = re.match(r"(minimi[sz]e|maximi[sz]e|restore|unmaximi[sz]e|full ?screen|hide)", text).group(1)
    act = {"minimise": "minimize", "maximise": "maximize", "restore": "unmaximize", "hide": "minimize",
           "unmaximize": "unmaximize", "unmaximise": "unmaximize", "fullscreen": "fullscreen",
           "full screen": "fullscreen"}.get(verb.replace("z", "s") if verb.endswith(("ize", "ise")) else verb,
                                            verb.replace("z", "s"))
    act = {"minimise": "minimize", "maximise": "maximize"}.get(act, act)
    obj = (m.group("o") or "").strip()
    if obj in ("all", "all windows", "everything", "everything on screen"):
        ctx.key("super+d")
        return Result("Showing the desktop.")
    if not ctx.bridge_ok():
        return None
    tgt = _target(obj)
    if tgt and len(tgt.split()) > 3:
        return None
    w = pick(ctx, tgt)
    if w is None:
        return Result(f"I can't find {'a ' + tgt if tgt else 'a window'} to {act}.", ok=False)
    return Result(_DONE[act]) if do_window(ctx, w, act) else None


@rule(r"(?:make|put|set|turn)\s+(?P<o>this|that|the current|the)?\s*(?:window\s+)?(?P<v>full ?screen|maximi[sz]ed|bigger)$|"
      r"(?:make|put|set|turn)\s+(?:the\s+)?(?P<t>[\w .\-]{2,24}?)\s+(?:window\s+)?(?P<v2>full ?screen)$", name="window_make", prio=29)
def window_make(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    v = (m.group("v") or m.group("v2") or "").replace(" ", "")
    act = "fullscreen" if "full" in v else "maximize"
    w = pick(ctx, _target(m.group("t") or ""))
    if w is None:
        return None
    return Result(_DONE[act]) if do_window(ctx, w, act) else None


@rule(r"(?:tile|put|snap|place)\s+(?:the\s+)?(?P<a>[\w .\-]{2,24}?)\s+(?:window\s+)?(?:on\s+the\s+|to\s+the\s+)?(?P<pa>left|right)\s+and\s+(?:the\s+)?(?P<b>[\w .\-]{2,24}?)\s+(?:window\s+)?(?:on\s+the\s+|to\s+the\s+)?(?P<pb>left|right)$",
      name="tile_pair", prio=31)
def tile_pair(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    wins = ctx.windows()
    a, b = match_windows(wins, m.group("a")), match_windows(wins, m.group("b"))
    if not a or not b:
        return None
    ctx.window_action(str(a[-1]["id"]), _TILES[m.group("pa")])
    ctx.window_action(str(b[-1]["id"]), _TILES[m.group("pb")])
    return Result("Arranged both windows.")


@rule(r"close(?:\s+(?P<o>this|that|the|current|active|it)(?:\s+window)?|\s+the\s+(?P<t>[\w .\-]{2,30}?)\s+window)$",
      name="close_window", prio=31)
def close_window(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    w = pick(ctx, _target(m.group("t") or ""))
    if w is None:
        return None
    return Result(_DONE["close"]) if do_window(ctx, w, "close") else None


_TILES = {"left": "tile_left", "right": "tile_right", "top": "tile_top", "bottom": "tile_bottom",
          "top left": "tile_topleft", "top right": "tile_topright",
          "bottom left": "tile_bottomleft", "bottom right": "tile_bottomright"}


@rule(r"(?:tile|snap|dock|put|move|send|stick|place)\s+(?:(?P<t>[\w .\-]{2,24}?)\s+)?(?:window\s+)?(?:to\s+|on\s+|at\s+|in\s+)?(?:the\s+)?"
      r"(?P<pos>top left|top right|bottom left|bottom right|left|right|top|bottom)\s*(?:half|side|corner|quarter|third)?$",
      name="tile", prio=32)
def tile(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    tgt = _target(m.group("t") or "")
    if tgt in ("workspace", "desktop", "monitor", "screen"):
        return None
    pos = m.group("pos")
    act = _TILES[pos]
    w = pick(ctx, tgt)
    if w is None:
        return None
    sc = w
    ctx.fly(sc["x"] + sc["w"] // 2, sc["y"] + 20, f"Moving to the {pos}", 0.7)
    res = ctx.window_action(str(w["id"]), act)
    ctx.release()
    return Result(f"Snapped {pos}.") if res and res.get("ok") else None


@rule(r"(?:split(?: the)? screen|side by side)\s+(?P<a>[\w .\-]{2,24}?)\s+(?:and|with)\s+(?P<b>[\w .\-]{2,24})$", name="split", prio=32)
def split(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    wins = ctx.windows()
    a, b = match_windows(wins, m.group("a")), match_windows(wins, m.group("b"))
    if not a or not b:
        return None
    ctx.window_action(str(a[-1]["id"]), "tile_left")
    ctx.window_action(str(b[-1]["id"]), "tile_right")
    return Result("Split the screen.")


@rule(r"(?:center|centre)\s+(?:this\s+|the\s+)?(?:window)?$", name="center", prio=32)
def center(ctx, m, text):
    w = pick(ctx, "") if ctx.bridge_ok() else None
    if not w:
        return None
    ctx.window_action(str(w["id"]), "tile_center")
    return Result("Centered.")


@rule(r"(?:keep|make|pin)\s+(?:this\s+|the\s+)?(?:window\s+)?(?:always\s+)?on top$|always on top$", name="above", prio=33)
def above(ctx, m, text):
    w = pick(ctx, "") if ctx.bridge_ok() else None
    if not w:
        return None
    ctx.window_action(str(w["id"]), "above")
    return Result("Keeping it on top.")


@rule(r"(?:stop keeping|unpin|remove|take)\s+(?:this\s+|the\s+)?(?:window\s+)?(?:from\s+)?(?:always\s+)?on top$", name="unabove", prio=33)
def unabove(ctx, m, text):
    w = pick(ctx, "") if ctx.bridge_ok() else None
    if not w:
        return None
    ctx.window_action(str(w["id"]), "unabove")
    return Result("No longer on top.")


@rule(r"(?:show|go to|take me to)\s+(?:the\s+)?desktop$|show desktop$", name="show_desktop", prio=33)
def show_desktop(ctx, m, text):
    ctx.key("super+d")
    return Result("")


@rule(r"(?:go|switch|jump|move)\s+to\s+(?:workspace|desktop)\s+(?P<n>\d+)$", name="workspace_n", prio=34)
def workspace_n(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    from screen import gnome_bridge as gb
    gb.switch_workspace(int(m.group("n")) - 1)
    return Result(f"Workspace {m.group('n')}.")


@rule(r"(?:go|switch|jump|move)\s+to\s+(?:the\s+)?(?P<d>next|previous|last)\s+(?:workspace|desktop)$|(?P<d2>next|previous)\s+workspace$",
      name="workspace_rel", prio=34)
def workspace_rel(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    from screen import gnome_bridge as gb
    ws = gb.workspaces()
    if not ws:
        return None
    d = (m.group("d") or m.group("d2"))
    cur, n = ws["current"], ws["count"]
    gb.switch_workspace((cur + 1) % n if d == "next" else (cur - 1) % n)
    return Result("")


@rule(r"(?:move|send)\s+(?:this\s+|the\s+)?(?:window\s+)?to\s+(?:workspace|desktop)\s+(?P<n>\d+)$|"
      r"(?:move|send)\s+(?:this\s+|the\s+)?(?:window\s+)?to\s+(?:the\s+)?(?P<d>next|previous)\s+(?:workspace|desktop)$",
      name="move_to_workspace", prio=34)
def move_to_workspace(ctx, m, text):
    if not ctx.bridge_ok():
        return None
    from screen import gnome_bridge as gb
    w = pick(ctx, "")
    if not w:
        return None
    if m.group("n"):
        idx = int(m.group("n")) - 1
    else:
        ws = gb.workspaces()
        idx = (ws["current"] + (1 if m.group("d") == "next" else -1)) % ws["count"]
    gb.move_window_to_workspace(str(w["id"]), idx)
    return Result(f"Moved to workspace {idx + 1}.")


@rule(r"(?:what(?:'s| is| windows are| apps are)?|which windows are|list(?: my)?|show)\s*(?:windows|apps)?\s*(?:are\s+)?open(?: right now)?$|"
      r"what(?:'s| is) open$|list (?:my )?windows$", name="list_windows", prio=35)
def list_windows(ctx, m, text):
    wins = ctx.windows()
    if not wins:
        return None
    names = []
    for w in reversed(wins):
        n = (w.get("title") or w.get("wm_class") or "").split(" - ")[-1][:28]
        if n and n not in names:
            names.append(n)
    return Result(f"You have {len(wins)} windows open: " + ", ".join(names[:6]) + ".")


@rule(r"(?:switch|go)\s+(?:to\s+)?(?:the\s+)?(?:previous|last|other|next)\s+(?:window|app)$|alt tab$|switch windows$", name="alt_tab", prio=35)
def alt_tab(ctx, m, text):
    ctx.key("alt+Tab")
    return Result("")
