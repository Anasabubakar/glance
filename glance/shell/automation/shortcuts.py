"""
shortcuts.py — say what you want, Glance presses the exact keys for the app you are in.

The same words mean different keys in different apps (copy in a terminal is ctrl+shift+c),
so the focused window picks the right combo.
"""

from __future__ import annotations

import re

from .registry import Result, rule

_CTX = (("terminal", ("terminal", "ptyxis", "konsole", "xterm", "kitty", "alacritty", "tilix")),
        ("firefox", ("firefox", "librewolf", "zen")),
        ("browser", ("brave", "chrome", "chromium", "edge", "vivaldi", "opera")),
        ("files", ("nautilus", "files", "dolphin", "nemo", "thunar")),
        ("code", ("code", "vscodium", "cursor", "sublime", "kate", "gedit", "texteditor", "text editor", "pluma")))


def context_of(ctx) -> str:
    w = next((w for w in ctx.windows() if w.get("focused")), None)
    if not w:
        return "any"
    hay = f"{w.get('wm_class', '')} {w.get('app', '')} {w.get('title', '')}".lower()
    for name, keys in _CTX:
        if any(k in hay for k in keys):
            return name
    return "any"


# phrase regex -> {context: combo}; "*" is the fallback; a list repeats/chains combos
TABLE = [
    (r"copy(?: that| this| it| the selection| selected text)?", {"terminal": "ctrl+shift+c", "*": "ctrl+c"}, "Copy"),
    (r"paste(?: that| it| here| the clipboard)?", {"terminal": "ctrl+shift+v", "*": "ctrl+v"}, "Paste"),
    (r"paste (?:as )?plain text|paste without formatting", {"*": "ctrl+shift+v"}, "Paste plain"),
    (r"cut(?: that| this| it| the selection)?", {"*": "ctrl+x"}, "Cut"),
    (r"undo(?: that| this| it| the last (?:thing|action|change))?|go back one step", {"*": "ctrl+z"}, "Undo"),
    (r"redo(?: that| it)?", {"*": "ctrl+shift+z"}, "Redo"),
    (r"select all(?: text)?|select everything", {"*": "ctrl+a"}, "Select all"),
    (r"save(?: it| this| the file| the document| my work| changes)?", {"*": "ctrl+s"}, "Save"),
    (r"save (?:it |this |the file |the document )?as(?: a new file)?", {"*": "ctrl+shift+s"}, "Save as"),
    (r"open (?:a )?file(?: dialog)?|open (?:the )?file chooser", {"*": "ctrl+o"}, "Open file"),
    (r"(?:new|create a new) (?:document|file|window|note)", {"*": "ctrl+n"}, "New"),
    (r"print(?: this| that| it| the)?(?: page| document| file)?", {"*": "ctrl+p"}, "Print"),
    (r"show all (?:the )?windows|show me all (?:my )?windows|overview", {"*": "super"}, "All windows"),
    (r"find(?: in (?:the )?(?:page|document|file))?|search (?:in )?(?:this|the) (?:page|document|file)", {"*": "ctrl+f"}, "Find"),
    (r"find and replace|replace text", {"code": "ctrl+h", "*": "ctrl+h"}, "Find and replace"),
    (r"zoom in|make it bigger|bigger text|increase (?:the )?zoom", {"*": "ctrl+plus"}, "Zoom in"),
    (r"zoom out|make it smaller|smaller text|decrease (?:the )?zoom", {"*": "ctrl+minus"}, "Zoom out"),
    (r"(?:reset|default|normal|actual size) zoom|reset the zoom", {"*": "ctrl+0"}, "Reset zoom"),
    (r"(?:make (?:it )?|toggle )?bold", {"*": "ctrl+b"}, "Bold"),
    (r"(?:make (?:it )?|toggle )?italic", {"*": "ctrl+i"}, "Italic"),
    (r"(?:make (?:it )?|toggle )?underline(?:d)?", {"*": "ctrl+u"}, "Underline"),
    # browser
    (r"(?:open )?(?:a )?new tab", {"terminal": "ctrl+shift+t", "files": "ctrl+t", "*": "ctrl+t"}, "New tab"),
    (r"close (?:this |the |current )?tab", {"terminal": "ctrl+shift+w", "*": "ctrl+w"}, "Close tab"),
    (r"(?:re-?open|restore|bring back|undo close)(?: the)?(?: last| closed)?(?: closed)? tab", {"*": "ctrl+shift+t"}, "Reopen tab"),
    (r"(?:go to |switch to )?(?:the )?next tab|tab (?:to the )?right", {"*": "ctrl+Tab"}, "Next tab"),
    (r"(?:go to |switch to )?(?:the )?(?:previous|last|prior) tab|tab (?:to the )?left", {"*": "ctrl+shift+Tab"}, "Previous tab"),
    (r"(?:refresh|reload)(?: the| this)?(?: page| tab)?", {"*": "F5"}, "Refresh"),
    (r"(?:hard|force) (?:refresh|reload)(?: the page)?|refresh without cache", {"*": "ctrl+shift+r"}, "Hard refresh"),
    (r"go back(?: a page| one page)?|back(?: a page)?|previous page", {"*": "alt+Left"}, "Back"),
    (r"go forward(?: a page| one page)?|forward(?: a page)?|next page", {"*": "alt+Right"}, "Forward"),
    (r"(?:go|take me) (?:to )?(?:the )?home ?page", {"*": "alt+Home"}, "Home page"),
    (r"bookmark(?: this| the)?(?: page| site| tab)?|add (?:this )?(?:page )?to bookmarks|favorite this page", {"*": "ctrl+d"}, "Bookmark"),
    (r"(?:show|open) (?:my )?bookmarks(?: manager)?", {"*": "ctrl+shift+o"}, "Bookmarks"),
    (r"(?:show|open) (?:my )?(?:browser )?history", {"files": "ctrl+h", "*": "ctrl+h"}, "History"),
    (r"(?:show|open) (?:my )?downloads", {"firefox": "ctrl+shift+y", "browser": "ctrl+j"}, "Downloads"),
    (r"(?:open )?(?:an? )?(?:incognito|private)(?: window| tab| mode)?|new private window", {"firefox": "ctrl+shift+p", "*": "ctrl+shift+n"}, "Private window"),
    (r"(?:open )?(?:the )?(?:developer tools|dev tools|devtools|inspect(?: element)?|inspector)", {"*": "F12"}, "Developer tools"),
    (r"view (?:the )?(?:page )?source", {"*": "ctrl+u"}, "View source"),
    (r"(?:go to|focus|select) (?:the )?(?:address bar|url bar|location bar|omnibox)", {"*": "ctrl+l"}, "Address bar"),
    (r"(?:go |toggle |exit |leave )?full ?screen(?: mode)?(?: on| off)?|toggle full screen", {"*": "F11"}, "Full screen"),
    (r"(?:go to|scroll to)(?: the)? top(?: of the page)?|jump to the top|back to the top", {"*": "ctrl+Home"}, "Top"),
    (r"(?:go to|scroll to)(?: the)? (?:bottom|end)(?: of the page)?|jump to the bottom", {"*": "ctrl+End"}, "Bottom"),
    (r"page down", {"*": "Page_Down"}, "Page down"),
    (r"page up", {"*": "Page_Up"}, "Page up"),
    # terminal
    (r"clear(?: the)?(?: terminal| screen| console)?", {"terminal": "ctrl+l"}, "Clear"),
    (r"(?:stop|cancel|interrupt|kill)(?: the| this)?(?: running)?(?: command| process| program)?", {"terminal": "ctrl+c"}, "Interrupt"),
    (r"(?:open )?(?:a )?new terminal window", {"terminal": "ctrl+shift+n"}, "New window"),
    # files
    (r"(?:create |make )?(?:a )?new folder", {"files": "ctrl+shift+n"}, "New folder"),
    (r"(?:show|toggle|hide) (?:the )?hidden files", {"files": "ctrl+h"}, "Hidden files"),
    (r"(?:go )?up(?: a| one)? (?:folder|level|directory)|parent folder", {"files": "alt+Up"}, "Up"),
    (r"rename(?: it| this| the file| the folder)?", {"files": "F2"}, "Rename"),
    (r"(?:show |open )?(?:file |item )?(?:properties|info|details)", {"files": "alt+Return"}, "Properties"),
    # editors
    (r"(?:comment|uncomment|toggle comment)(?: out)?(?: this| the)?(?: line| selection)?", {"code": "ctrl+slash"}, "Comment"),
    (r"duplicate(?: this| the)? line", {"code": "ctrl+shift+d"}, "Duplicate line"),
    (r"(?:go to|jump to) line(?: number)?", {"code": "ctrl+g"}, "Go to line"),
    (r"(?:open|show) (?:the )?command palette", {"code": "ctrl+shift+p"}, "Command palette"),
    (r"(?:toggle|show|hide) (?:the )?sidebar", {"code": "ctrl+b"}, "Sidebar"),
    (r"(?:format|prettify|tidy)(?: the)?(?: document| code| file)", {"code": "shift+alt+f"}, "Format"),
    # system keys
    (r"(?:show|open) (?:the )?(?:activities|overview)|activities", {"*": "super"}, "Activities"),
    (r"(?:show|open) (?:the )?(?:app grid|all apps|applications)", {"*": "super+a"}, "All apps"),
    (r"(?:show|open) (?:my )?notifications|notification center", {"*": "super+v"}, "Notifications"),
    (r"(?:open|show) (?:the )?(?:run dialog|run command)", {"*": "alt+F2"}, "Run command"),
    (r"(?:open|show) (?:the )?emoji (?:picker|keyboard)|emoji", {"*": "ctrl+period"}, "Emoji"),
    (r"(?:switch|change) (?:the )?(?:keyboard |input )?(?:language|layout)", {"*": "super+space"}, "Input language"),
    (r"press\s+(?:the\s+)?(?:enter|return)(?: key)?|hit enter", {"*": "Return"}, "Enter"),
    (r"press\s+(?:the\s+)?escape(?: key)?|hit escape|dismiss|cancel that|close (?:this )?(?:dialog|popup|menu)", {"*": "Escape"}, "Escape"),
    (r"press\s+(?:the\s+)?tab(?: key)?|next field", {"*": "Tab"}, "Tab"),
    (r"press\s+(?:the\s+)?(?:space|spacebar)(?: key)?", {"*": "space"}, "Space"),
    (r"press\s+(?:the\s+)?backspace(?: key)?|delete (?:that|the last (?:letter|character))", {"*": "BackSpace"}, "Backspace"),
    (r"press\s+(?:the\s+)?delete(?: key)?", {"*": "Delete"}, "Delete"),
    (r"press\s+(?:the\s+)?(?P<d>up|down|left|right)(?: arrow)?(?: key)?", {"*": "ARROW"}, "Arrow"),
]
_COMPILED = [(re.compile(rf"(?:{p})$", re.I), table, label) for p, table, label in TABLE]


def _dry(text: str) -> bool:
    return any(rx.match(text) for rx, _t, _l in _COMPILED)


@rule(r".+", name="shortcut", prio=69, dry=_dry)
def shortcut(ctx, m, text):
    for rx, table, label in _COMPILED:
        mm = rx.match(text)
        if not mm:
            continue
        if not ctx.bridge_ok() and not ctx.actuator():
            return None
        c = context_of(ctx)
        combo = table.get(c) or (table.get("*") if c != "any" or "*" in table else None)
        if c in ("browser", "firefox") and c not in table:
            combo = table.get("browser") or table.get("*")
        if combo is None:
            return None                       # a shortcut that only exists in another kind of app
        if combo == "ARROW":
            combo = mm.groupdict().get("d", "Down").capitalize() if mm.groupdict().get("d") else None
        ctx.caption(label, 0.4)
        ctx.key(combo)
        return Result("")
    return None


@rule(r"type\s+(?:out\s+)?(?P<t>.+)$", name="type_text", prio=57, numbers=False,
      dry=lambda s: _typeable(s) is not None)
def type_text(ctx, m, text):
    t = _typeable(text)
    if t is None:
        return None
    ctx.type_text(t)
    return Result("")


def _typeable(text: str):
    """The text to type for "type hello world", or None for things that need the screen
    ("type something in the editor") or the AI."""
    m = re.match(r"type\s+(?:out\s+)?(?P<t>.+)$", text.strip(), re.I)
    if not m:
        return None
    t = m.group("t").strip()
    quoted = len(t) > 1 and t[0] in "\"“'" and t[-1] in "\"”'"
    vague = re.match(r"(?:something|anything|a |an |some |it\b|that\b|this\b|your |my )", t, re.I)
    place = re.search(r"\b(?:in|into|on|inside|at|to)\s+(?:the|my|this|that|a|an)\b", t, re.I)
    if quoted:
        return t[1:-1]
    return None if (vague or place) else t


@rule(r"(?:go to|switch to|open|jump to|select)\s+tab\s+(?P<n>[1-8])$", name="tab_n", prio=58)
def tab_n(ctx, m, text):
    c = context_of(ctx)
    ctx.caption(f"Tab {m.group('n')}", 0.4)
    ctx.key(("alt+" if c == "firefox" else "ctrl+") + m.group("n"))
    return Result("")


@rule(r"(?:go to|switch to|jump to)\s+(?:the\s+)?last tab$", name="tab_last", prio=58)
def tab_last(ctx, m, text):
    ctx.key("ctrl+9")
    return Result("")


@rule(r"scroll\s+(?P<d>up|down)(?:\s+(?P<a>a (?:little|bit|lot)|a lot|a little|a bit|more|\d+))?(?:\s+(?:a (?:little|bit)|bit))?$", name="scroll", prio=58)
def scroll(ctx, m, text):
    a = m.group("a") or ""
    n = int(a) if a.isdigit() else 12 if "lot" in a else 3 if ("little" in a or "bit" in a) else 6
    ctx.scroll(n if m.group("d") == "up" else -n)
    return Result("")
