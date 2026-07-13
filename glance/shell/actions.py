"""
actions.py — everything Glance DOES on the machine.

  * the computer-use agent loop (`_run_task`): screenshot -> Claude picks an
    action -> execute -> fresh screenshot, until done
  * app/URL launching (exe paths + URL protocols + web-app fallback)
  * the voice-driven organizer (journaled, reversible, icon-sort finish)
  * Google Workspace tools (opt-in API path)
  * background research agents that report back during a lull

Safety model: the file organizer is move-only + undoable by construction;
the agent acts directly (like Glance) with prompt-level restraint on
irreversible actions, a step cap, and Esc to stop.
"""

from __future__ import annotations

import asyncio
import os
import re
import time

from config import cfg
from session_log import slog
from screen.capture import capture_all_screens
from ui.panel import AppState


class ActionsMixin:
    def _get_actuator(self):
        if getattr(self, "_actuator", None) is None:
            import sys as _sys
            if _sys.platform == "win32":
                from glance.agent.actuation import WindowsActuator
                self._actuator = WindowsActuator()
            else:
                from glance.agent.actuation import LinuxActuator
                self._actuator = LinuxActuator()
        return self._actuator

    def _tidy_desktop_icons(self):
        """Sort desktop icons by name. Windows-only (COM/WM_COMMAND);
        no-op on Linux where the file manager owns icon layout."""
        import sys as _sys
        if _sys.platform != "win32":
            return
        try:
            import comtypes
            try:
                comtypes.CoInitialize()      # brain thread needs its own COM init
            except Exception:
                pass
            import comtypes.client
            from comtypes.automation import VARIANT
            shell = comtypes.client.CreateObject("Shell.Application", dynamic=True)
            # SWC_DESKTOP=8, SWFO_NEEDDISPATCH=1
            disp = shell.Windows().FindWindowSW(VARIANT(), VARIANT(), 8, 0, 1)
            disp.Document.SortColumns = "prop:System.ItemNameDisplay;"
            slog("ACT", "desktop icons sorted by name (COM)")
            return
        except Exception as e:
            slog("ERROR", f"COM icon sort failed ({e}) — trying legacy post")
        try:
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            WM_COMMAND, SORT_BY_NAME = 0x0111, 0x7021
            # The live icon view can sit under Progman OR a WorkerW (Win11 often
            # keeps a STALE empty view under Progman) — find them ALL and post the
            # sort to each; the dead ones ignore it, the real one sorts.
            found = []
            prog = u.FindWindowW("Progman", None)
            h = u.FindWindowExW(prog, 0, "SHELLDLL_DefView", None)
            if h:
                found.append(h)

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _enum(hwnd, _l):
                dv = u.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                if dv and dv not in found:
                    found.append(dv)
                return True
            u.EnumWindows(_enum, 0)

            if found:
                for dv in found:
                    u.PostMessageW(dv, WM_COMMAND, SORT_BY_NAME, 0)
                slog("ACT", f"icon sort posted to {len(found)} desktop view(s)")
            else:
                slog("ERROR", "desktop view window not found (no icon sort)")
        except Exception as e:
            slog("ERROR", f"icon sort failed: {e}")

    async def _run_organize_voice(self, transcript: str):
        """Voice-wired folder organizer — the 'hands + undo' signature skill.
        Runs the existing journaled organize engine (home-folder-only, move-only,
        fully reversible), then speaks a short summary. 'Undo' puts it all back."""
        s = transcript.lower()
        from pathlib import Path as _P
        root, which = _P.home() / "Desktop", "desktop"
        if "download" in s:
            root, which = _P.home() / "Downloads", "downloads folder"
        elif "document" in s:
            root, which = _P.home() / "Documents", "documents folder"
        slog("ACT", f"organize {root}")
        try:
            from glance import config as _cli_cfg
            from glance.providers import get_provider
            from glance.agent.runtime import run_organize
            try:
                prov_name = _cli_cfg.active_provider()
                model = None
                if prov_name == "claude":
                    # Grouping files doesn't need the big model — Haiku plans a
                    # 25-file desktop in a few seconds vs ~20s+ on Sonnet.
                    model = os.environ.get("GLANCE_ORGANIZE_MODEL",
                                           "claude-haiku-4-5-20251001")
                provider = get_provider(prov_name, model=model)
            except Exception:
                provider = get_provider("heuristic")   # zero-config fallback
            # Stagger the moves so icons visibly vanish one by one — reads as
            # live work on camera instead of a jump cut. GLANCE_MOVE_STAGGER=0
            # to disable.
            stagger = float(os.environ.get("GLANCE_MOVE_STAGGER", "0.12") or 0)
            try:
                sess, plan = await asyncio.to_thread(run_organize, root,
                                                     provider, False, stagger)
            except Exception as e:
                # LLM plan failed (bad JSON / network / timeout) → the heuristic
                # sorter still tidies by type, so the command never just dies.
                slog("ERROR", f"organize via {provider.name} failed: {e} "
                     "— retrying with heuristic")
                provider = get_provider("heuristic")
                sess, plan = await asyncio.to_thread(run_organize, root,
                                                     provider, False, stagger)
        except Exception as e:
            slog("ERROR", f"organize failed: {e}")
            await self._reply_local("Hmm, I couldn't tidy that up just now.")
            return
        n = len(sess.batch.records) if getattr(sess, "batch", None) else 0
        slog("ACT", f"organize done: {n} file(s) moved")
        if not n:
            await self._reply_local(
                f"Your {which} already looks tidy — nothing to move.")
            return
        tidy = ""
        if which == "desktop":
            self._tidy_desktop_icons()   # finishing touch: sort what's left by name
            tidy = ", and tidied up what's left"
        folders = sorted({m.dest_folder for m in plan.moves}) if plan.moves else []
        into = ""
        if folders:
            into = " into " + ", ".join(folders[:3]) + \
                   (" and more" if len(folders) > 3 else "")
        await self._reply_local(
            f"Done — I moved {n} file{'s' if n != 1 else ''}{into}{tidy}. "
            "Say 'undo' if you want everything back.")

    async def _run_undo_voice(self):
        """Reverse the last organize — shared by the instant local 'undo' command
        and the router's undo route (so ANY phrasing works, not just the keyword)."""
        from glance.agent import journal as _org_journal
        stagger = float(os.environ.get("GLANCE_MOVE_STAGGER", "0.12") or 0)
        msg = await asyncio.to_thread(_org_journal.undo_last, stagger)
        slog("ACT", f"undo: {msg}")
        await self._reply_local(msg)

    def _call_workspace(self, name: str, inp: dict):
        """Dispatch one Workspace tool to the Google API (blocking — run in a
        thread). Returns JSON-able data the model then summarizes for the ear."""
        import google_workspace as gw
        if name == "gmail_list":
            return gw.gmail_list(inp.get("query", "is:unread"), int(inp.get("count", 5)))
        if name == "gmail_send":
            return gw.gmail_send(inp.get("to", ""), inp.get("subject", ""),
                                 inp.get("body", ""))
        if name == "calendar_events":
            return gw.calendar_events(int(inp.get("count", 10)), int(inp.get("days", 1)))
        return {"error": f"unknown tool {name}"}

    async def _run_workspace(self, instruction: str):
        """Opt-in reliable path: a small tool-use loop over the Gmail/Calendar API
        (no screen, no clicking), then ONE short spoken summary. Dispatches to
        the active provider's tool-use API."""
        provider = cfg.llm_provider()
        if provider == "claude" and cfg.anthropic_api_key:
            await self._run_workspace_anthropic(instruction)
        elif provider in ("openai", "copilot") and cfg.openai_api_key:
            await self._run_workspace_openai(instruction)
        else:
            await self._run_workspace_generic(instruction)

    def _ws_tools_schema(self):
        """Shared workspace tool definitions (Anthropic format)."""
        return [
            {"name": "gmail_list",
             "description": "List Gmail messages matching a search query (default "
                            "'is:unread'). Returns from/subject/snippet.",
             "input_schema": {"type": "object", "properties": {
                 "query": {"type": "string"}, "count": {"type": "integer"}},
                 "additionalProperties": False}},
            {"name": "gmail_send",
             "description": "Send an email. Use ONLY when the user clearly asked to "
                            "send one; state the recipient in your spoken reply.",
             "input_schema": {"type": "object", "properties": {
                 "to": {"type": "string"}, "subject": {"type": "string"},
                 "body": {"type": "string"}},
                 "required": ["to", "subject", "body"], "additionalProperties": False}},
            {"name": "calendar_events",
             "description": "List upcoming Google Calendar events. days=1 for today.",
             "input_schema": {"type": "object", "properties": {
                 "count": {"type": "integer"}, "days": {"type": "integer"}},
                 "additionalProperties": False}},
        ]

    def _ws_system(self):
        return (
            "You are Glance, handling the user's Gmail and Google Calendar through "
            "these tools. Use them to get what you need, then reply in ONE short, "
            "natural spoken line for the ear — summarize, never read raw data or "
            "email addresses aloud. Only send an email when the user clearly asked "
            "to, and name the recipient in your reply. Keep it warm and brief.")

    async def _run_workspace_anthropic(self, instruction: str):
        """Workspace via Anthropic tool-use."""
        import json
        WS_TOOLS = self._ws_tools_schema()
        system = self._ws_system()
        client = self._get_anthropic()
        messages = [{"role": "user", "content": instruction}]
        self._emit_state(AppState.THINKING)
        try:
            for _ in range(6):
                resp = await client.messages.create(
                    model=cfg.vision_model(), max_tokens=1024,
                    system=system, tools=WS_TOOLS, messages=messages)
                messages.append({"role": "assistant",
                                 "content": [b.model_dump() for b in resp.content]})
                tool_uses = [b for b in resp.content if b.type == "tool_use"]
                text = " ".join(b.text for b in resp.content if b.type == "text")
                if not tool_uses:
                    await self._reply_local(text or "Done.")
                    return
                results = []
                for tu in tool_uses:
                    try:
                        data = await asyncio.to_thread(
                            self._call_workspace, tu.name, tu.input or {})
                        content = json.dumps(data)[:4000]
                    except Exception as e:
                        content = f"error: {e}"
                    results.append({"type": "tool_result",
                                    "tool_use_id": tu.id, "content": content})
                messages.append({"role": "user", "content": results})
        except Exception as e:
            print("[glance-debug] workspace error:", e, flush=True)
            await self._reply_local("I couldn't reach your Google account just now.")

    async def _run_workspace_openai(self, instruction: str):
        """Workspace via OpenAI function calling."""
        import json
        from openai import AsyncOpenAI

        tools = [
            {"type": "function", "function": {
                "name": t["name"], "description": t["description"],
                "parameters": t["input_schema"]}}
            for t in self._ws_tools_schema()
        ]
        system = self._ws_system()
        client = AsyncOpenAI(api_key=cfg.openai_api_key)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": instruction},
        ]
        self._emit_state(AppState.THINKING)
        try:
            for _ in range(6):
                resp = await client.chat.completions.create(
                    model=cfg.vision_model(), max_tokens=1024,
                    tools=tools, messages=messages)
                choice = resp.choices[0]
                msg = choice.message
                messages.append(msg.model_dump(exclude_none=True))
                if not msg.tool_calls:
                    await self._reply_local(msg.content or "Done.")
                    return
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments) if isinstance(
                        tc.function.arguments, str) else tc.function.arguments
                    try:
                        data = await asyncio.to_thread(
                            self._call_workspace, tc.function.name, args)
                        content = json.dumps(data)[:4000]
                    except Exception as e:
                        content = f"error: {e}"
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": content})
        except Exception as e:
            print("[glance-debug] workspace openai error:", e, flush=True)
            await self._reply_local("I couldn't reach your Google account just now.")

    async def _run_workspace_generic(self, instruction: str):
        """Workspace via text-based tool calls for Gemini/Ollama/others."""
        import json as _json

        tool_desc = (
            "Available tools (reply with JSON to use one):\n"
            '  {"tool":"gmail_list","query":"is:unread","count":5}\n'
            '  {"tool":"gmail_send","to":"x@y.com","subject":"Hi","body":"..."}\n'
            '  {"tool":"calendar_events","count":10,"days":1}\n'
            '  {"tool":"done","summary":"your spoken summary here"}\n'
        )
        system = self._ws_system() + "\n\n" + tool_desc
        self._emit_state(AppState.THINKING)
        context = ""
        try:
            for _ in range(6):
                prompt = instruction if _ == 0 else f"Tool result: {context}\nContinue or say done."
                full = ""
                async for chunk in self._get_llm().stream_response(
                    user_text=prompt, screenshots_b64=[], history=[],
                    system_prompt=system, model=cfg.fast_model(),
                ):
                    full += chunk

                text = full.strip()
                if "```" in text:
                    text = text.split("```")[1].strip()
                    if text.startswith("json"):
                        text = text[4:].strip()
                try:
                    action = _json.loads(text)
                except Exception:
                    import re as _re
                    m = _re.search(r'\{[^}]+\}', text)
                    if m:
                        try:
                            action = _json.loads(m.group())
                        except Exception:
                            await self._reply_local(text[:200])
                            return
                    else:
                        await self._reply_local(text[:200])
                        return

                tool = action.pop("tool", "done")
                if tool == "done":
                    await self._reply_local(action.get("summary", text[:200]))
                    return
                try:
                    data = await asyncio.to_thread(self._call_workspace, tool, action)
                    context = _json.dumps(data)[:4000]
                except Exception as e:
                    context = f"error: {e}"
        except Exception as e:
            print("[glance-debug] workspace generic error:", e, flush=True)
            await self._reply_local("I couldn't reach your Google account just now.")

    async def _spawn_background(self, description: str):
        """Fire-and-forget: kick off a background agent that works the task and
        reports back, so the foreground stays free for you to keep talking. This is
        for NON-screen work (research, lookups) — a background agent can't drive the
        live mouse without fighting you, so screen tasks stay in the foreground."""
        self._bg_counter += 1
        tid = self._bg_counter
        self._bg[tid] = {"desc": description.strip(), "status": "running",
                         "result": None}
        await self._reply_local("On it — I'll look into that and report back.")
        self._bg[tid]["task"] = asyncio.create_task(self._bg_worker(tid, description))

    async def _bg_worker(self, tid: int, description: str):
        try:
            result = await self._research_agent(description)
            self._bg[tid].update(status="done", result=result)
        except Exception as e:
            print("[glance-debug] bg worker error:", e, flush=True)
            self._bg[tid].update(status="error")
            result = "I ran into a problem looking into that."
        await self._bg_report(tid, result)

    async def _research_agent(self, description: str) -> str:
        """Background research via the active provider. Uses web search when
        available (Anthropic web_search, OpenAI web_search_preview, or
        DuckDuckGo fallback). Returns a short spoken line."""
        provider = cfg.llm_provider()

        if provider == "claude" and cfg.anthropic_api_key:
            return await self._research_anthropic(description)
        if provider in ("openai", "copilot") and cfg.openai_api_key:
            return await self._research_openai(description)

        # Gemini/Ollama/others: web-search via DuckDuckGo, then summarize
        return await self._research_generic(description)

    async def _research_anthropic(self, description: str) -> str:
        """Research via Anthropic web_search tool."""
        client = self._get_anthropic()
        system = ("You are a research aide for Glance. Investigate the request (use "
                  "web search when it helps), then answer in a concise, spoken-style "
                  "summary — 2 to 4 sentences for the ear, lead with the answer, no "
                  "URLs, citations, or markdown.")
        for tools in ([{"type": "web_search_20250305", "name": "web_search",
                        "max_uses": 5}], []):
            try:
                messages = [{"role": "user", "content": description}]
                for _ in range(4):
                    resp = await client.messages.create(
                        model=cfg.vision_model(), max_tokens=1024,
                        system=system, tools=tools, messages=messages)
                    if resp.stop_reason == "pause_turn":
                        messages.append({"role": "assistant",
                            "content": [b.model_dump() for b in resp.content]})
                        continue
                    text = " ".join(b.text for b in resp.content
                                    if b.type == "text").strip()
                    if text:
                        return text
                    break
            except Exception as e:
                print(f"[glance-debug] research anthropic (search={bool(tools)}) error: {e}",
                      flush=True)
        return "I couldn't dig up a solid answer on that."

    async def _research_openai(self, description: str) -> str:
        """Research via OpenAI with web_search_preview tool."""
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=cfg.openai_api_key)
        system = ("You are a research aide. Investigate the request using web search, "
                  "then answer in a concise, spoken-style summary — 2 to 4 sentences "
                  "for the ear, lead with the answer, no URLs or markdown.")
        try:
            resp = await client.responses.create(
                model=cfg.vision_model(),
                tools=[{"type": "web_search_preview"}],
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": description},
                ],
            )
            text = "".join(item.text for item in resp.output if hasattr(item, "text")).strip()
            if text:
                return text
        except Exception as e:
            print(f"[glance-debug] research openai error: {e}", flush=True)
        # Fallback: no search
        try:
            resp = await client.chat.completions.create(
                model=cfg.vision_model(), max_tokens=1024,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": description},
                ])
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception as e:
            print(f"[glance-debug] research openai fallback error: {e}", flush=True)
        return "I couldn't dig up a solid answer on that."

    async def _research_generic(self, description: str) -> str:
        """Research for Gemini/Ollama/others: DuckDuckGo search + LLM summary."""
        search_results = ""
        try:
            from ai.web_search import search
            search_results = await search(description) or ""
        except Exception:
            pass

        system = ("You are a research aide. Answer in a concise, spoken-style "
                  "summary — 2 to 4 sentences for the ear, lead with the answer, "
                  "no URLs or markdown.")
        if search_results:
            from ai.web_search import build_search_context
            system += build_search_context(search_results)

        full = ""
        try:
            async for chunk in self._get_llm().stream_response(
                user_text=description, screenshots_b64=[], history=[],
                system_prompt=system, model=cfg.vision_model(),
            ):
                full += chunk
        except Exception as e:
            print(f"[glance-debug] research generic error: {e}", flush=True)
        return full.strip() or "I couldn't dig up a solid answer on that."

    async def _bg_report(self, tid: int, result: str):
        """Report back during a lull, so we never talk over an active turn."""
        for _ in range(180):                       # wait up to ~3 min for idle
            if self._state == AppState.IDLE:
                break
            await asyncio.sleep(1.0)
        await self._reply_local(f"Quick update — {result}")

    def _bg_block(self) -> str:
        """Prompt fragment so the foreground can answer 'what are you working on?'"""
        running = [t["desc"] for t in self._bg.values()
                   if t.get("status") == "running"]
        if not running:
            return ""
        return ("\n\nBACKGROUND TASKS you're working on right now (mention if asked): "
                + "; ".join(running))

    def _action_label(self, text, inp):
        """Short pointer-bubble tag during a task — prefer the model's own terse
        note, else derive one from the action. Kept tight for the little pill."""
        t = " ".join((text or "").split()[:5]).strip(" .!?")
        if t:
            return t[:36]
        a = (inp.get("action") or "").lower()
        if a == "type":
            s = (inp.get("text") or "").strip()
            return f"typing “{s[:16]}”" if s else "typing"
        if a == "key":
            return f"pressing {inp.get('text', '')}".strip()
        if a == "scroll":
            return "scrolling"
        if "double" in a:
            return "double-click"
        if "right" in a:
            return "right-click"
        if "click" in a:
            return "clicking"
        return ""

    def _exec_action(self, actuator, action, px, py, text):
        """Run one computer-tool action on the real machine (physical coords)."""
        a = (action or "").lower()
        slog("ACT", f"{a} @ ({px},{py})" + (f" text={text[:30]!r}" if text else ""))
        if a in ("left_click", "click") and px is not None:
            actuator.left_click(px, py)
        elif a == "double_click" and px is not None:
            actuator.double_click(px, py)
        elif a == "right_click" and px is not None:
            actuator.right_click(px, py)
        elif a in ("mouse_move", "cursor_move") and px is not None:
            actuator.move(px, py)
        elif a in ("left_click_drag",) and px is not None:
            actuator.left_click(px, py)          # simplified: click destination
        elif a == "type" and text:
            actuator.type_text(text)
        elif a == "key" and text:
            actuator.key(text)
        elif a == "scroll" and px is not None:
            actuator.scroll(px, py, -3)
        # screenshot / cursor_position / wait: no-op — the loop re-captures anyway.

    # Apps `start <name>` can't resolve (no App Paths entry). Each maps to a list
    # of candidates tried in order: absolute exe paths (if they exist) and URL
    # protocols. First hit wins; unknown names fall through to plain `start`.
    _APP_LAUNCHERS_WIN = {
        "steam": [r"C:\Program Files (x86)\Steam\steam.exe", "steam://open/main"],
        "discord": [r"%LOCALAPPDATA%\Discord\Update.exe|--processStart|Discord.exe",
                    "discord://"],
        "spotify": [r"%APPDATA%\Spotify\Spotify.exe", "spotify:"],
        "epic games": ["com.epicgames.launcher://apps"],
        "epic": ["com.epicgames.launcher://apps"],
        "telegram": [r"%APPDATA%\Telegram Desktop\Telegram.exe", "tg://"],
        "slack": [r"%LOCALAPPDATA%\Microsoft\WindowsApps\Slack.exe",
                  r"%LOCALAPPDATA%\slack\slack.exe",
                  r"C:\Program Files\Slack\slack.exe"],
        "notion": [r"%LOCALAPPDATA%\Programs\Notion\Notion.exe", "notion://"],
    }

    _APP_LAUNCHERS_LINUX = {
        "steam": ["steam"],
        "discord": ["discord"],
        "spotify": ["spotify"],
        "telegram": ["telegram-desktop", "telegram"],
        "slack": ["slack"],
        "notion": ["notion-app", "notion"],
        "firefox": ["firefox"],
        "chrome": ["google-chrome", "google-chrome-stable", "chromium-browser"],
        "code": ["code"],
        "vscode": ["code"],
        "files": ["nautilus", "thunar", "dolphin", "nemo"],
        "terminal": ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"],
        "text editor": ["gedit", "kate", "mousepad"],
        "calculator": ["gnome-calculator", "kcalc"],
        "notepad": ["gedit", "kate", "mousepad", "xed"],
    }

    @property
    def _APP_LAUNCHERS(self):
        import sys as _sys
        return self._APP_LAUNCHERS_WIN if _sys.platform == "win32" else self._APP_LAUNCHERS_LINUX

    def _app_launchers(self) -> dict:
        """Built-in launcher map merged with the user's ``~/.glance/apps.json``:

            {"my app": ["C:\\\\path\\\\to\\\\app.exe", "myapp://"], "other": "other://"}

        Candidates are tried in order (exe paths checked for existence, then URL
        protocols). User entries override built-ins — so 'Windows can't find X'
        is fixable per-machine without touching code."""
        cached = getattr(self, "_app_launchers_cache", None)
        if cached is not None:
            return cached
        merged = dict(self._APP_LAUNCHERS)
        try:
            import json
            from pathlib import Path
            p = Path.home() / ".glance" / "apps.json"
            if p.exists():
                user = json.loads(p.read_text(encoding="utf-8"))
                for k, v in user.items():
                    merged[k.strip().lower()] = [v] if isinstance(v, str) else list(v)
                slog("ACT", f"loaded {len(user)} custom app launcher(s) from apps.json")
        except Exception as e:
            slog("ERROR", f"~/.glance/apps.json ignored ({e})")
        self._app_launchers_cache = merged
        return merged

    def _launch_app(self, name: str):
        """Open an app directly (fast, reliable) instead of driving the GUI.
        Known tricky apps launch via exe path / URL protocol (Windows) or
        binary name (Linux); others fall through to OS-level defaults."""
        name = (name or "").strip()
        if not name:
            return
        import os
        import sys as _sys
        import subprocess
        for cand in self._app_launchers().get(name.lower(), []):
            if _sys.platform == "win32":
                if "://" in cand or cand.endswith(":"):
                    try:
                        os.startfile(cand)
                        slog("ACT", f"launched '{name}' via {cand}")
                        return
                    except Exception:
                        continue
                parts = [os.path.expandvars(p) for p in cand.split("|")]
                if os.path.isfile(parts[0]):
                    try:
                        subprocess.Popen(parts)
                        slog("ACT", f"launched '{name}' via {parts[0]}")
                        return
                    except Exception:
                        continue
            else:
                try:
                    subprocess.Popen(
                        [cand], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    slog("ACT", f"launched '{name}' via {cand}")
                    return
                except FileNotFoundError:
                    continue
                except Exception:
                    continue
        if name.lower() in self._WEB_APPS:
            slog("ACT", f"'{name}' not installed locally -> web app")
            self._open_url(name)
            return
        if _sys.platform == "win32":
            try:
                subprocess.Popen(["cmd", "/c", "start", "", name],
                                 creationflags=0x08000000)
            except Exception:
                try:
                    os.startfile(name)
                except Exception as e:
                    print("[glance-debug] launch error:", e, flush=True)
        else:
            try:
                subprocess.Popen(
                    ["xdg-open", name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as e:
                print("[glance-debug] launch error:", e, flush=True)

    # Common web apps → their URL, so "check my email" opens the real logged-in
    # web app in the user's browser (no OAuth, no API — Glance reads/acts with its
    # hands). This is our take on OpenGlance's Workspace integration.
    _WEB_APPS = {
        "gmail": "https://mail.google.com", "email": "https://mail.google.com",
        "google calendar": "https://calendar.google.com",
        "calendar": "https://calendar.google.com",
        "google drive": "https://drive.google.com", "drive": "https://drive.google.com",
        "google docs": "https://docs.google.com", "docs": "https://docs.google.com",
        "google sheets": "https://sheets.google.com", "sheets": "https://sheets.google.com",
        "youtube": "https://youtube.com", "maps": "https://maps.google.com",
        "gemini": "https://gemini.google.com", "chatgpt": "https://chatgpt.com",
        "slack": "https://app.slack.com/client", "notion": "https://notion.so",
    }

    def _open_url(self, target: str):
        """Open a URL or a known web app (gmail, calendar, …) in the default
        browser — the user's logged-in session. `start` routes URLs to the browser."""
        t = (target or "").strip()
        if not t:
            return
        t = self._WEB_APPS.get(t.lower(), t)
        if not re.match(r"^[a-z][a-z0-9+.-]*://", t, re.I):
            t = "https://" + t
        self._launch_app(t)

    async def _say_task(self, text):
        """Speak a short closing line during a computer-use task."""
        text = (text or "").strip()
        if not text:
            return
        ends = list(re.finditer(r"[.!?](?=\s|$)", text))
        spoken = text
        if len(ends) >= 2:
            spoken = text[:ends[1].end()].strip()
        if len(spoken) > 200 and ends:
            spoken = text[:ends[0].end()].strip()
        self.sig_response_chunk.emit(spoken + " ")
        self._emit_state(AppState.SPEAKING)
        try:
            await self._get_tts().speak(spoken)
        except Exception:
            slog("ERROR", "closing TTS failed")

    async def _run_task(self, instruction: str):
        """The general computer-use agent. Loops screenshot → model picks an
        action → we run it on the real machine → fresh screenshot → repeat, until
        the task is done. Dispatches to the active provider's computer-use API:
          • Claude → Anthropic Computer Use API
          • OpenAI → Responses API with computer_use_preview
          • Others → text-based tool-call fallback
        Safety: prompt-level + step cap + Esc-to-stop."""
        provider = cfg.llm_provider()
        if provider == "claude" and cfg.anthropic_api_key:
            await self._run_task_anthropic(instruction)
        elif provider == "openai" and cfg.openai_api_key:
            await self._run_task_openai(instruction)
        else:
            await self._run_task_generic(instruction)

    async def _run_task_generic(self, instruction: str):
        """Fallback computer-use via text-based tool calls for any provider."""
        import base64
        import json as _json
        from ai.element_locator import _pick_resolution, _resize_jpeg

        try:
            actuator = self._get_actuator()
        except Exception as e:
            self.sig_error.emit(str(e))
            await self._reply_local("I can't drive the mouse and keyboard right now.")
            return
        shots = capture_all_screens()
        if not shots:
            await self._reply_local("I can't see your screen right now.")
            return
        tw, th = _pick_resolution(shots[0].width, shots[0].height)

        def grab():
            s = capture_all_screens()
            if not s:
                return None, None
            shot = s[0]
            b64 = base64.b64encode(
                _resize_jpeg(base64.b64decode(shot.base64_jpeg), tw, th)).decode("ascii")
            return shot, b64

        def to_coords(shot, cx, cy):
            cx = max(0.0, min(float(cx), tw)); cy = max(0.0, min(float(cy), th))
            pw = shot.physical_width or shot.width
            ph = shot.physical_height or shot.height
            vx = cx / tw * pw + shot.physical_left
            vy = cy / th * ph + shot.physical_top
            scale = shot.dpi_scale if shot.dpi_scale > 0 else 1.0
            return int(round(vx / scale)), int(round(vy / scale)), int(round(vx)), int(round(vy))

        system = (
            "You are Glance, doing a task on the user's screen. You can see a "
            "screenshot. Reply with a JSON action to perform. Available actions:\n"
            '  {"action":"click","x":123,"y":456,"text":"clicking Save"}\n'
            '  {"action":"double_click","x":123,"y":456,"text":"opening file"}\n'
            '  {"action":"right_click","x":123,"y":456,"text":"context menu"}\n'
            '  {"action":"type","content":"hello world","text":"typing greeting"}\n'
            '  {"action":"key","content":"ctrl+s","text":"saving"}\n'
            '  {"action":"scroll","x":123,"y":456,"direction":"down","text":"scrolling"}\n'
            '  {"action":"launch_app","name":"notepad","text":"opening notepad"}\n'
            '  {"action":"open_url","target":"gmail","text":"opening email"}\n'
            '  {"action":"done","text":"All done — enjoy!"}\n\n'
            f"Screen resolution: {tw}x{th}. Coordinates are pixels from top-left.\n"
            "Work ONE action at a time. After each, you'll get a fresh screenshot.\n"
            "When finished, use the 'done' action with a short spoken summary.\n"
            "SAFETY: do NOT send, delete, buy, or post unless the task asks for it."
        )
        mem, sk = self._memory.facts_block(), self._memory.skills_block()
        if mem or sk:
            system += "\n\n" + "\n\n".join(x for x in (mem, sk) if x)

        shot, b64 = grab()
        self._cancel_flag = False
        self._emit_state(AppState.THINKING)
        MAX_STEPS = 12
        try:
            for _ in range(MAX_STEPS):
                if self._cancel_flag:
                    await self._say_task("Okay, stopping.")
                    break
                full = ""
                async for chunk in self._get_llm().stream_response(
                    user_text=instruction if _ == 0 else "Here's the updated screenshot. Continue the task or say done.",
                    screenshots_b64=[b64] if b64 else [],
                    history=[],
                    system_prompt=system,
                    model=cfg.vision_model(),
                ):
                    full += chunk
                # Parse JSON action from response
                text = full.strip()
                if "```" in text:
                    text = text.split("```")[1].strip()
                    if text.startswith("json"):
                        text = text[4:].strip()
                try:
                    action = _json.loads(text)
                except Exception:
                    # Try to find JSON in the response
                    import re as _re
                    m = _re.search(r'\{[^}]+\}', text)
                    if m:
                        try:
                            action = _json.loads(m.group())
                        except Exception:
                            await self._say_task(text[:200])
                            break
                    else:
                        await self._say_task(text[:200])
                        break

                act = (action.get("action") or "").lower()
                label = action.get("text", "")

                if act == "done":
                    await self._say_task(label or "Done.")
                    break
                elif act == "launch_app":
                    self._launch_app(action.get("name", ""))
                elif act == "open_url":
                    self._open_url(action.get("target", ""))
                elif act in ("click", "left_click"):
                    x, y = int(action.get("x", 0)), int(action.get("y", 0))
                    lx, ly, px, py = to_coords(shot, x, y)
                    self.sig_point_at.emit(float(lx), float(ly), label)
                    self._exec_action(actuator, "left_click", px, py, "")
                elif act == "double_click":
                    x, y = int(action.get("x", 0)), int(action.get("y", 0))
                    lx, ly, px, py = to_coords(shot, x, y)
                    self.sig_point_at.emit(float(lx), float(ly), label)
                    self._exec_action(actuator, "double_click", px, py, "")
                elif act == "right_click":
                    x, y = int(action.get("x", 0)), int(action.get("y", 0))
                    lx, ly, px, py = to_coords(shot, x, y)
                    self.sig_point_at.emit(float(lx), float(ly), label)
                    self._exec_action(actuator, "right_click", px, py, "")
                elif act == "type":
                    self._exec_action(actuator, "type", None, None, action.get("content", ""))
                elif act == "key":
                    self._exec_action(actuator, "key", None, None, action.get("content", ""))
                elif act == "scroll":
                    x, y = int(action.get("x", 0)), int(action.get("y", 0))
                    _, _, px, py = to_coords(shot, x, y)
                    self._exec_action(actuator, "scroll", px, py, "")
                else:
                    await self._say_task(label or full[:100])
                    break

                opened_url = act == "open_url"
                await asyncio.sleep(1.8 if opened_url else 0.8)
                shot, b64 = grab()
                if shot is None:
                    break
        except Exception as e:
            import traceback
            print("[glance-debug] generic task error:", flush=True)
            traceback.print_exc()
            self.sig_error.emit(str(e))
        finally:
            self.sig_point_release.emit()

    async def _run_task_openai(self, instruction: str):
        """Computer-use agent via OpenAI's Responses API (computer_use_preview)."""
        import base64
        from openai import AsyncOpenAI
        from ai.element_locator import _pick_resolution, _resize_jpeg

        try:
            actuator = self._get_actuator()
        except Exception as e:
            self.sig_error.emit(str(e))
            await self._reply_local("I can't drive the mouse and keyboard right now.")
            return
        shots = capture_all_screens()
        if not shots:
            await self._reply_local("I can't see your screen right now.")
            return
        tw, th = _pick_resolution(shots[0].width, shots[0].height)

        def grab():
            s = capture_all_screens()
            if not s:
                return None, None
            shot = s[0]
            b64 = base64.b64encode(
                _resize_jpeg(base64.b64decode(shot.base64_jpeg), tw, th)).decode("ascii")
            return shot, b64

        def to_coords(shot, cx, cy):
            cx = max(0.0, min(float(cx), tw)); cy = max(0.0, min(float(cy), th))
            pw = shot.physical_width or shot.width
            ph = shot.physical_height or shot.height
            vx = cx / tw * pw + shot.physical_left
            vy = cy / th * ph + shot.physical_top
            scale = shot.dpi_scale if shot.dpi_scale > 0 else 1.0
            return int(round(vx / scale)), int(round(vy / scale)), int(round(vx)), int(round(vy))

        system = (
            "You are Glance, doing a task on the user's screen with the "
            "computer tool. Work ONE action at a time. To open an app, use the "
            "launch_app function. For websites, use open_url. "
            "THE MOMENT the goal is achieved, STOP. "
            "Speak ONLY when finished: ONE short sentence about the outcome. "
            "SAFETY: do NOT send, delete, buy, or post unless the task asks for it."
        )
        mem, sk = self._memory.facts_block(), self._memory.skills_block()
        if mem or sk:
            system += "\n\n" + "\n\n".join(x for x in (mem, sk) if x)

        client = AsyncOpenAI(api_key=cfg.openai_api_key)
        tools = [
            {"type": "computer_use_preview", "display_width": tw, "display_height": th,
             "environment": "browser"},
            {"type": "function", "name": "launch_app",
             "description": "Open an app by name (e.g. 'notepad', 'chrome').",
             "parameters": {"type": "object", "properties": {"name": {"type": "string"}},
                           "required": ["name"]}},
            {"type": "function", "name": "open_url",
             "description": "Open a URL or web app (e.g. 'gmail', 'youtube', or a full URL).",
             "parameters": {"type": "object", "properties": {"target": {"type": "string"}},
                           "required": ["target"]}},
        ]
        shot, b64 = grab()
        input_msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                {"type": "input_text", "text": instruction},
            ]},
        ]

        self._cancel_flag = False
        self._emit_state(AppState.THINKING)
        MAX_STEPS = 12
        try:
            for _ in range(MAX_STEPS):
                if self._cancel_flag:
                    await self._say_task("Okay, stopping.")
                    break
                resp = await client.responses.create(
                    model=cfg.vision_model(),
                    tools=tools,
                    input=input_msgs,
                    truncation="auto",
                )
                # Process the response output items
                has_tool_call = False
                text_output = ""
                for item in resp.output:
                    if item.type == "text":
                        text_output += item.text
                    elif item.type == "computer_call":
                        has_tool_call = True
                        action = item.action
                        coord = getattr(action, "coordinate", None) or getattr(action, "x", None)
                        if hasattr(action, "type"):
                            act_type = action.type
                            px = py = None
                            if coord and hasattr(action, "x") and hasattr(action, "y"):
                                lx, ly, px, py = to_coords(shot, action.x, action.y)
                                self.sig_point_at.emit(float(lx), float(ly),
                                                       act_type[:20])
                            text = getattr(action, "text", "") or ""
                            self._exec_action(actuator, act_type, px, py, text)
                    elif item.type == "function_call":
                        has_tool_call = True
                        import json as _json
                        args = _json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                        if item.name == "launch_app":
                            self._launch_app(args.get("name", ""))
                        elif item.name == "open_url":
                            self._open_url(args.get("target", ""))

                if not has_tool_call:
                    await self._say_task(text_output or "Done.")
                    break

                await asyncio.sleep(0.8)
                shot, b64 = grab()
                if shot is None:
                    break
                # Feed the screenshot back as the next input
                input_msgs = resp.output + [
                    {"type": "computer_call_output",
                     "call_id": next((i.call_id for i in resp.output if i.type == "computer_call"), ""),
                     "output": {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"}},
                ]
        except Exception as e:
            import traceback
            print("[glance-debug] openai task error:", flush=True)
            traceback.print_exc()
            self.sig_error.emit(str(e))
        finally:
            self.sig_point_release.emit()

    async def _run_task_anthropic(self, instruction: str):
        """Computer-use agent via Anthropic's Computer Use API (original path)."""
        import base64
        import httpx
        from ai.element_locator import (_pick_resolution, _resize_jpeg,
                                         _API_URL, _BETA_HEADER)

        api_key = cfg.anthropic_api_key
        try:
            actuator = self._get_actuator()
        except Exception as e:
            self.sig_error.emit(str(e))
            await self._reply_local("I can't drive the mouse and keyboard right now.")
            return
        shots = capture_all_screens()
        if not shots:
            await self._reply_local("I can't see your screen right now.")
            return
        tw, th = _pick_resolution(shots[0].width, shots[0].height)

        def grab():
            s = capture_all_screens()
            if not s:
                return None, None
            shot = s[0]
            b64 = base64.b64encode(
                _resize_jpeg(base64.b64decode(shot.base64_jpeg), tw, th)).decode("ascii")
            return shot, b64

        def to_coords(shot, cx, cy):
            cx = max(0.0, min(float(cx), tw)); cy = max(0.0, min(float(cy), th))
            pw = shot.physical_width or shot.width
            ph = shot.physical_height or shot.height
            vx = cx / tw * pw + shot.physical_left
            vy = cy / th * ph + shot.physical_top
            scale = shot.dpi_scale if shot.dpi_scale > 0 else 1.0
            return int(round(vx / scale)), int(round(vy / scale)), int(round(vx)), int(round(vy))

        async def say(text):
            await self._say_task(text)

        system = (
            "You are Glance, doing a task on the user's Windows screen with the "
            "computer tool. Work ONE action at a time: take an action, then you'll "
            "get a fresh screenshot of the result, then decide the next one. To open "
            "an app, use the launch_app tool — it opens it directly and reliably; do "
            "NOT drive the Start menu for that. For email, calendar, documents, or "
            "any website, use open_url (e.g. 'gmail', 'calendar', or a full URL) — it "
            "opens the user's logged-in web app in their browser; then read and act "
            "on it with the computer tool. "
            "With each tool call, include a VERY short text label (2-4 words) of "
            "what you're doing right then — e.g. 'clicking Save', 'opening the File "
            "menu', 'typing the address'. It shows as a tiny tag next to the cursor "
            "and is NOT read aloud, so keep it terse; never mention keystrokes, "
            "coordinates, or 'screenshot'. Do NOT speak (voice) during the steps. "
            "THE MOMENT the goal is visibly achieved, STOP — no extra clicks, no "
            "adjusting, no double-checking (e.g. once the video is playing, you are "
            "DONE; another click might pause it). "
            "Speak ONLY when finished (or when you stop to defer something): give "
            "ONE short sentence, under 15 words, about the outcome — e.g. 'Lofi's "
            "on — enjoy!' Never recap the steps you took. "
            "SAFETY: do NOT send, delete, buy, post, or pay for anything unless the "
            "task explicitly asks for it. If it does, do everything up to that step, "
            "then STOP with a closing line and NO tool call, saying what's left for "
            "the user to confirm."
        )
        mem, sk = self._memory.facts_block(), self._memory.skills_block()
        if mem or sk:
            system += "\n\n" + "\n\n".join(x for x in (mem, sk) if x)
        launch_tool = {
            "name": "launch_app",
            "description": ("Open a Windows app directly by name — fast and reliable, "
                            "no Start-menu driving. `name` is the app's common/exe "
                            "name, e.g. 'notepad', 'chrome', 'calc', 'explorer'."),
            "input_schema": {"type": "object",
                             "properties": {"name": {"type": "string"}},
                             "required": ["name"], "additionalProperties": False},
        }
        open_url_tool = {
            "name": "open_url",
            "description": ("Open a web page or web app in the user's default browser "
                            "(their logged-in session), then read/act on it with the "
                            "computer tool. `target` is a full URL or a known app name: "
                            "gmail, calendar, drive, docs, sheets, youtube, maps. Use "
                            "this for email, calendar, documents, and any website "
                            "instead of typing into the address bar."),
            "input_schema": {"type": "object",
                             "properties": {"target": {"type": "string"}},
                             "required": ["target"], "additionalProperties": False},
        }
        tools = [{"type": "computer_20251124", "name": "computer",
                  "display_width_px": tw, "display_height_px": th},
                 launch_tool, open_url_tool]
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01",
                   "anthropic-beta": _BETA_HEADER, "content-type": "application/json"}
        shot, b64 = grab()
        messages = [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
             "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": instruction}]}]

        self._cancel_flag = False
        self._emit_state(AppState.THINKING)
        MAX_STEPS = 12
        try:
            import contextlib
            # Shared warm client (nullcontext → don't close the shared pool on exit)
            async with contextlib.nullcontext(self._get_http()) as http:
                for _ in range(MAX_STEPS):
                    if self._cancel_flag:
                        await say("Okay, stopping.")
                        break
                    body = {"model": cfg.vision_model(), "max_tokens": 1024,
                            "system": system, "tools": tools, "messages": messages}
                    r = await http.post(_API_URL, json=body, headers=headers)
                    if r.status_code >= 400:
                        print(f"[glance-debug] task HTTP {r.status_code}: "
                              f"{r.text[:300]}", flush=True)
                        break
                    content = r.json().get("content", [])
                    messages.append({"role": "assistant", "content": content})
                    text = " ".join(b.get("text", "") for b in content
                                    if b.get("type") == "text")
                    tool_uses = [b for b in content if b.get("type") == "tool_use"]
                    if not tool_uses:
                        await say(text)                # only the closing / defer line
                        break                          # task done / stopped to confirm

                    for tu in tool_uses:
                        inp = tu.get("input") or {}
                        if tu.get("name") == "launch_app":
                            self._launch_app(inp.get("name", ""))
                            continue
                        if tu.get("name") == "open_url":
                            self._open_url(inp.get("target", ""))
                            continue
                        coord = inp.get("coordinate")
                        px = py = None
                        if coord and len(coord) == 2:
                            lx, ly, px, py = to_coords(shot, coord[0], coord[1])
                            self.sig_point_at.emit(float(lx), float(ly),
                                                   self._action_label(text, inp))
                        try:
                            self._exec_action(actuator, inp.get("action"), px, py,
                                              inp.get("text"))
                        except Exception:
                            print("[glance-debug] action error:", flush=True)
                            import traceback
                            traceback.print_exc()

                    # Web pages need longer to load than a local app window.
                    opened_url = any(t.get("name") == "open_url" for t in tool_uses)
                    await asyncio.sleep(1.8 if opened_url else 0.8)
                    shot, b64 = grab()
                    if shot is None:
                        break
                    result_img = {"type": "image", "source": {"type": "base64",
                                  "media_type": "image/jpeg", "data": b64}}
                    results = []
                    for tu in tool_uses:
                        blocks = []
                        if tu.get("name") == "launch_app":
                            blocks.append({"type": "text", "text":
                                f"Opened {(tu.get('input') or {}).get('name','')}."})
                        elif tu.get("name") == "open_url":
                            blocks.append({"type": "text", "text":
                                f"Opened {(tu.get('input') or {}).get('target','')} "
                                "in the browser."})
                        blocks.append(result_img)
                        results.append({"type": "tool_result",
                                        "tool_use_id": tu["id"], "content": blocks})
                    messages.append({"role": "user", "content": results})
        except Exception as e:
            import traceback
            print("[glance-debug] task error:", flush=True)
            traceback.print_exc()
            self.sig_error.emit(str(e))
        finally:
            self.sig_point_release.emit()

