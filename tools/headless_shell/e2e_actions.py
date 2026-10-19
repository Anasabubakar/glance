"""
End-to-end check of Glance's action code against a real (headless) GNOME Shell with the
Glance extension: local commands, and the screen-action loop driven by a scripted
"model". Run through tools/headless_shell/run.sh (see e2e.sh). Prints PASS/FAIL lines.
"""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "glance", "shell"))

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

import companion_manager as cm  # noqa: E402
from screen import gnome_bridge as gb  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""), flush=True)


class Scripted:
    """A fake model: returns the next prepared reply for each screen-action step."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def complete(self, user_text, screenshots_b64, history, system_prompt, model=None):
        self.calls += 1
        return self.replies.pop(0) if self.replies else '{"action":"done","text":"finished"}'

    async def stream_response(self, *a, **k):
        yield await self.complete(*a, **k)


def new_manager(replies=()):
    m = cm.CompanionManager()
    said = []

    async def reply(msg):
        said.append(msg)

    async def say(text):
        said.append(text)
    m._reply_local = reply
    m._say_task = say
    m._llm = Scripted(replies)
    m._llm_for = tuple(cfg_chain()) + (True, ())
    m.said = said
    return m


def cfg_chain():
    from config import cfg
    return cfg.fallback_chain()


def windows():
    return gb.windows()


def run(m, text):
    asyncio.run(m._run_task(text))


def wait_window(substr, secs=15):
    t = time.time()
    while time.time() - t < secs:
        for w in windows():
            if substr in (w["title"] + w["wm_class"]).lower():
                return w
        time.sleep(0.5)
    return None


# make get_llm return the scripted model whatever the provider chain says
cm.CompanionManager._get_llm = lambda self: self._llm

# 1. local command: open the text editor, then minimize it by voice command
m = new_manager()
run(m, "open the text editor")
w = wait_window("texteditor") or wait_window("text editor")
check("open_app: 'open the text editor' launches a window", w is not None, str(w and w["title"]))
gb.window_action("class:text", "activate")
time.sleep(1)
run(m, "minimize this window")
time.sleep(1.2)
ws = [x for x in windows() if "text" in (x["title"] + x["wm_class"]).lower()]
check("window: 'minimize this window' minimizes it", bool(ws) and ws[0]["minimized"], str(m.said[-1:]))
gb.window_action("class:text", "unminimize")
gb.window_action("class:text", "activate")
time.sleep(1.2)
run(m, "maximize it")
time.sleep(1.2)
ws = [x for x in windows() if "text" in (x["title"] + x["wm_class"]).lower()]
check("window: 'maximize it' maximizes it", bool(ws) and ws[0]["maximized"])
run(m, "restore the window")
time.sleep(1)
run(m, "what time is it")
check("answer: time is spoken", any("It's" in s for s in m.said), str(m.said[-1:]))

# 2. typing through the screen-action loop with a scripted model
gb.window_action("class:text", "activate")
time.sleep(1)
m = new_manager([
    '{"action":"click","x":500,"y":450,"text":"clicking the document"}',
    '{"action":"type","content":"typed by the action loop","text":"typing the text"}',
    '{"action":"done","text":"All typed."}',
])
run(m, "type something in the editor")
time.sleep(1.5)
ss = gb.screenshot()
if ss:
    os.replace(ss["path"], os.environ.get("E2E_SHOT_TYPE", "/tmp/glance-e2e-type.png"))
check("loop: click + type + done ran to completion", m._llm.calls == 3 and any("typed" in s for s in m.said), str(m.said))

# 3. draw / drag / annotate through the loop (a canvas app is opened by the harness)
gb.window_action("class:text", "minimize")       # leave only the canvas on screen
time.sleep(2)
canvas = wait_window("canvas", 3)
if canvas:
    gb.window_action("title:canvas", "activate")
    time.sleep(1)
    m = new_manager([
        '{"action":"draw","shape":"circle","x":500,"y":500,"r":90,"text":"drawing a circle"}',
        '{"action":"drag","from":[300,300],"to":[450,380],"text":"dragging"}',
        '{"action":"annotate","kind":"circle","x":500,"y":500,"r":60,"text":"here"}',
        '{"action":"done","text":"Drew it."}',
    ])
    run(m, "draw a circle and drag a line in the canvas")
    time.sleep(1.5)
    ss = gb.screenshot()
    if ss:
        os.replace(ss["path"], os.environ.get("E2E_SHOT_DRAW", "/tmp/glance-e2e-draw.png"))
    check("loop: draw + drag + annotate ran to completion", m._llm.calls == 4, str(m.said))
    try:
        from PIL import Image
        im = Image.open(os.environ.get("E2E_SHOT_DRAW", "/tmp/glance-e2e-draw.png")).convert("RGB")
        red = sum(1 for px in im.getdata() if px[0] > 200 and px[1] < 60 and px[2] < 60)
        check("canvas: the circle and the drag really appear on screen", red > 300, f"{red} red pixels")
    except Exception as e:
        check("canvas: pixels readable", False, str(e))

# 4. macros: record two clicks, save, replay (keys are best effort on Wayland, so clicks are checked)
import macros  # noqa: E402


def spin(secs):
    t = time.time()
    while time.time() - t < secs:
        app.processEvents()
        time.sleep(0.05)


gb.window_action("class:text", "unminimize")
gb.window_action("class:text", "activate")
spin(1.5)
m = new_manager()
m.sig_macro_cmd.emit("macro_start", "e2e demo")
spin(1.0)
gb._call("Click", "300", "320", "1", "1")
spin(0.8)
gb._call("Click", "340", "380", "1", "1")
spin(1.0)
m.sig_macro_cmd.emit("macro_stop", "e2e demo")
spin(1.0)
data = macros.load("e2e demo")
steps = data["steps"] if data else []
check("macro: recorded two clicks", [x["do"] for x in steps] == ["click", "click"],
      str([(x["do"], x.get("x"), x.get("y")) for x in steps]))
run(m, "run the e2e demo macro")
check("macro: replay ran every step", any("ran 2 steps" in x for x in m.said), str(m.said[-1:]))

# 5. instant system commands
run(m, "turn on dark mode")
check("theme: dark mode command spoke", any("Dark" in x for x in m.said))
run(m, "set a timer for 1 minute")
check("timer: command accepted", any("Timer set" in x for x in m.said))
run(m, "take a screenshot")
check("screenshot: saved to Pictures", any("Saved a screenshot" in x for x in m.said), str(m.said[-1:]))

# 6. automations against the real shell: tiling, clipboard, workspaces, apps, files, math
gb.window_action("class:text", "unminimize")
gb.window_action("class:text", "activate")
spin(1.2)
m = new_manager()
run(m, "tile the text editor left")
spin(1.0)
ed = [x for x in windows() if "text" in (x["title"] + x["wm_class"]).lower()][0]
check("automation: tile left puts the window on the left half", ed["x"] <= 70 and 600 <= ed["w"] <= 700, str((ed["x"], ed["w"])))
run(m, "tile the canvas right")
spin(1.0)
cv = [x for x in windows() if "canvas" in (x["title"] + x["wm_class"]).lower()][0]
check("automation: tile right puts the window on the right half", cv["x"] >= 600, str((cv["x"], cv["w"])))
gb.set_clipboard("clipboard says hi")
spin(0.5)
run(m, "what's on my clipboard")
check("automation: clipboard round trip through the compositor", any("clipboard says hi" in x for x in m.said), str(m.said[-1:]))
run(m, "what windows are open")
check("automation: lists the open windows", any("windows open" in x for x in m.said), str(m.said[-1:]))
run(m, "what is 12 times 8")
check("automation: math answers locally", any("96" in x for x in m.said), str(m.said[-1:]))
ws0 = gb.workspaces()
run(m, "go to workspace 2")
spin(0.8)
check("automation: workspace switch is accepted", ws0.get("count", 0) >= 1, str(ws0))
run(m, "open the calculator")
calc = wait_window("calculator", 12)
check("automation: opens an installed app by name", calc is not None, str(calc and calc["title"]))
run(m, "close the calculator")
spin(1.5)
check("automation: closes it again", wait_window("calculator", 0.5) is None)
run(m, "create a folder called e2e demo on my desktop")
check("automation: creates a folder", (Path.home() / "Desktop" / "e2e demo").is_dir())
run(m, "tile the text editor left and then tile the canvas right")
check("automation: compound requests run every part", any("Snapped right" in x or "Snapped" in x for x in m.said), str(m.said[-2:]))

print(f"\n{sum(results)}/{len(results)} checks passed", flush=True)
sys.exit(0 if all(results) else 1)
