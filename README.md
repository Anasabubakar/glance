# Glance

**Talk to your computer — she sees your screen, points at things, and actually does them.**

Glance is a voice-first AI desktop companion for **Windows** and **Linux** (Debian/Ubuntu). Hold a hotkey, talk, and she:

- **sees** your screen and answers questions about it,
- **points** — a little buddy flies to whatever you're asking about (snaps to the real UI element, pixel-accurate),
- **acts** — opens apps, clicks, types, runs multi-step tasks via Claude Computer Use,
- **remembers** you across sessions and **learns routines** you teach her by voice,
- **tours** an app — "explain my screen" gives you a spoken, pointing walkthrough.

Her brain is **Claude** (Sonnet 5 + Computer Use); voice via **Deepgram** streaming STT and free **Edge TTS**.

> **Early build.** The core loop — talk, see, point, act — works and is genuinely fun. But speech recognition isn't perfect, and the more advanced features (multi-step tasks, background research) are lightly tested. This is a "try it and tell me what breaks" release, not a finished product.

---

## What works today

**The voice companion — `glance run`:**

- Push-to-talk voice; an on-screen buddy that points at what you ask about.
- *"What's on my screen?"* — a spoken answer, buddy points at the relevant thing.
- *"Explain my screen"* / *"walk me through this"* — a teaching tour that points out several things, one at a time.
- *"Open Notepad and type hello"*, *"click the Save button"*, *"go to YouTube"* — she acts on your machine.
- *"Remember I prefer dark mode"*, *"save this as my morning routine"* — cross-session memory + learned routines.
- *"Go research X and tell me later"* — a background agent works while you keep talking.

**The file organizer — `glance organize`:**

- Tidies a folder from one LLM call; move-only and **fully reversible** with `glance undo`.

---

## Getting started

You'll need an **Anthropic API key** (Glance's brain) and ideally a **Deepgram key**
(fast, accurate voice — free tier; without it she falls back to slower local Whisper).

### Windows 10/11

**Option A — Download the app** *(no Python needed)*

1. Grab **`Glance-v0.1.0-windows.zip`** from [**Releases**](https://github.com/Anasabubakar/glance/releases/latest)
2. Extract anywhere and run `Glance.exe`
   *(the exe is unsigned, so SmartScreen may warn on first run — "More info, Run anyway")*
3. The setup wizard walks you through your keys
4. **Hold `Ctrl+Alt+M`, say *"what's on my screen?"*, and release**

**Option B — Run from source** *(Python 3.10+)*

```powershell
git clone https://github.com/Anasabubakar/glance.git
cd glance
pip install -e ".[shell,claude]"
glance run
```

### Linux (Debian/Ubuntu)

```bash
git clone https://github.com/Anasabubakar/glance.git
cd glance

# System deps (PyQt6, audio, accessibility)
sudo apt install python3-pyqt6 libportaudio2 at-spi2-core xdotool

pip install -e ".[shell,claude]"
glance run
```

### Keys

Let the setup wizard collect them, or copy `.env.example` to `glance/shell/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
DEEPGRAM_API_KEY=...
GLANCE_ACTIVE_LLM=claude
```

### Just want the file organizer? (no voice, no keys)

```bash
pip install -e .
glance organize ~/Desktop -p heuristic --dry-run   # preview, zero config
glance organize ~/Desktop                           # do it
glance undo                                          # reverse it
```

---

## Platform support

| Feature | Windows | Linux |
|---------|---------|-------|
| Voice companion (push-to-talk, STT/TTS) | Yes | Yes |
| Screen capture + vision | Yes | Yes |
| Pointing overlay (buddy) | Yes | Yes |
| UI element snapping | UIA tree | AT-SPI2 |
| Computer Use (click/type/launch) | Yes | Yes |
| App launcher | Native | xdg-open |
| File organizer | Yes | Yes |
| .exe installer | Yes | N/A |
| .deb package | N/A | Planned |

---

## A note on safety

The **file organizer** is move-only and fully reversible (`glance undo`). The **voice agent acts directly** — she does what you ask rather than nagging for permission — but she stops and hands back before genuinely irreversible, high-stakes actions (send, delete, buy). It's an early build acting on your real machine, so **watch her, and press `Esc` to stop at any time.**

## Layout

```
glance/
  shell/        # the voice + screen companion (glance run) — the main app
    routing.py  #   intent routing: local fast-paths + Haiku router
    tour.py     #   guided screen tour + pointing (inline [POINT] tags)
    actions.py  #   computer-use agent, launchers, organizer, background agents
  agent/        # computer-use actuation, permission model, safe file ops + undo
  providers/    # Claude / OpenAI / Gemini / Ollama / heuristic, behind one interface
  platform/     # OS-specific backends (Windows UIA, Linux AT-SPI2, app launchers)
  cli.py        # glance organize / undo / run
docs/           # USAGE.md (start here), plus design docs
tests/          # headless tests with a fake provider
packaging/      # PyInstaller (Windows .exe), .deb (Linux)
organizer/      # early file-organizer prototype — superseded by glance/, kept for its tests
```

## Roadmap

- **Linux platform layer** — AT-SPI2 for UI-tree snapping, xdg-open for app launching, full parity with Windows.
- **Learnable skills (SKILL.md)** — teach Glance new routines by voice.
- **Glance Bridge (MCP)** — exposing her eyes and pointer as an MCP server so any agent can see and point at your screen.
- **.deb packaging** — one-command install on Debian/Ubuntu.
- **Better desktop control** — opt-in shortcut/icon arrangement, more launcher coverage.

Issues and PRs very welcome — this is an early build and the fastest way to shape it.

## Credits & license

Glance is an independent project by [Anas Abubakar](https://github.com/Anasabubakar). It builds on ideas and open-source work from:

- **Clicky** by [@farzaa](https://github.com/farzaa/clicky) — the original macOS screen-companion concept (MIT).
- **Clicky for Windows** by [Bitshank-2338 / Shashank Singh](https://github.com/Bitshank-2338/clicky-windows) — the Python/PyQt6 Windows companion Glance lifts its voice + pointing pipeline from (MIT).
- **OpenClicky** by [@jasonkneen](https://github.com/jasonkneen/openclicky) — the actively maintained open-source Clicky with Agent Mode; design reference (MIT, macOS/Swift).

Glance is released under the [MIT License](LICENSE). It is not affiliated with or endorsed by the above projects or Anthropic.
