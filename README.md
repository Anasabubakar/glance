<p align="center">
  <img src="glance.png" alt="Glance" width="180">
</p>

<h1 align="center">Glance</h1>

<p align="center">
  <strong>Open-source AI desktop companion — sees your screen, points at things, and acts on them.</strong>
</p>

<p align="center">
  <a href="#install">Install</a> •
  <a href="#how-it-works">How it works</a> •
  <a href="#providers">Providers</a> •
  <a href="#building-from-source">Build from source</a> •
  <a href="#roadmap">Roadmap</a>
</p>

---

Glance is a voice-first AI desktop companion for **Windows** and **Linux**. Hold a hotkey, talk, and she:

- **Sees** your screen and answers questions about it
- **Points** — a cursor buddy flies to the thing you asked about (pixel-accurate, snaps to real UI elements)
- **Acts** — opens apps, clicks, types, runs multi-step tasks via Claude Computer Use
- **Remembers** you across sessions and learns routines you teach by voice
- **Tours** an app — *"explain my screen"* gives a spoken, pointing walkthrough

Works with **Claude**, **OpenAI**, **Gemini**, **GitHub Copilot**, or fully offline with **Ollama** (no API keys needed).

> **Early build.** The core loop — talk, see, point, act — works. Speech recognition isn't perfect, and the more advanced features (multi-step tasks, background research) are lightly tested. Feedback and PRs welcome.

---

## Install

### Windows 10/11

**Option A — Installer (recommended, no Python needed)**

1. Download **`Setup-Glance.exe`** from [Releases](https://github.com/Anasabubakar/glance/releases/latest)
2. Run the installer — optionally lets you install Ollama for free local AI
3. Launch Glance from the desktop shortcut or Start menu
4. The setup wizard walks you through your API keys (or skip for Ollama-only mode)
5. **Hold `Ctrl+Alt+M`, say *"what's on my screen?"*, and release**

> The exe is unsigned, so SmartScreen may warn on first run — click "More info → Run anyway".

**Option B — Portable zip**

Download `Glance-windows.zip` from Releases, extract anywhere, run `Glance.exe`.

---

### Linux (Ubuntu / Debian)

**Option A — .deb package (recommended)**

```bash
# Download the latest .deb from Releases
sudo apt install ./glance_0.1.0_amd64.deb

# Launch
glance-companion
```

The .deb installs desktop integration (app menu entry, icons) and all dependencies.

**Option B — AppImage (any distro)**

```bash
# Download from Releases
chmod +x Glance-0.1.0-x86_64.AppImage
./Glance-0.1.0-x86_64.AppImage
```

No installation needed — runs on any Linux with FUSE support.

---

### Run from source (any platform, Python 3.10+)

```bash
git clone https://github.com/Anasabubakar/glance.git
cd glance

# Install core + companion shell + Claude provider
pip install -e ".[shell,claude]"

# Linux only — system deps for PyQt6 and audio
sudo apt install libportaudio2 libgl1-mesa-dev libegl1-mesa-dev libxkbcommon-dev

# Launch the companion
glance run
```

---

## How it works

| What you do | What Glance does |
|-------------|-----------------|
| Hold `Ctrl+Alt+M` and speak | Records audio, transcribes with Whisper (local) or Deepgram (cloud) |
| Release the hotkey | Captures your screen, sends screenshot + transcript to the LLM |
| Wait ~2 seconds | LLM responds with text + pointing coordinates |
| Watch | Glance speaks the answer and moves the cursor buddy to the target |

The companion lives in the system tray. Right-click for provider switching, Ollama model management, recording, diagnostics, and settings.

### Push-to-talk hotkey

Default: **Ctrl+Alt+M** (configurable via `GLANCE_HOTKEY` in `.env`).

Press **Esc** at any time to cancel the current response.

---

## Providers

| Provider | API Key? | Best for |
|----------|----------|----------|
| **Ollama** | No (free, local) | Privacy, offline use, zero cost |
| **Claude** | Yes | Best quality (vision + computer use) |
| **OpenAI** | Yes | GPT-4o vision |
| **Gemini** | Yes | Google AI Studio (free tier available) |
| **GitHub Copilot** | Copilot subscription | Free models via your existing seat |

Switch providers at runtime from the tray menu — no restart needed.

### Ollama (free, offline)

Glance's setup wizard installs Ollama and pulls a vision model for you. Or manually:

```bash
# Install Ollama (https://ollama.com)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a vision model
ollama pull llama3.2-vision

# Set in your .env
GLANCE_ACTIVE_LLM=ollama
```

---

## Configuration

On first launch, the setup wizard collects your preferences. To configure manually, copy `.env.example`:

- **From source:** `cp .env.example glance/shell/.env`
- **Installed (Windows):** edit `%LOCALAPPDATA%\Glance\.env`
- **Installed (Linux):** edit `~/.local/share/Glance/.env`

Key settings:

```bash
ANTHROPIC_API_KEY=sk-ant-...      # Claude (primary LLM)
DEEPGRAM_API_KEY=...              # Fast cloud STT (optional)
GLANCE_ACTIVE_LLM=claude          # claude | openai | gemini | ollama
GLANCE_HOTKEY=ctrl+alt+m          # Push-to-talk hotkey
WHISPER_MODEL=small.en            # Local STT model size
```

---

## File organizer

Glance also includes a standalone file organizer (no voice, no GUI):

```bash
pip install -e .
glance organize ~/Desktop --dry-run   # preview (no API key needed with heuristic)
glance organize ~/Desktop              # do it
glance undo                            # fully reversible
```

---

## Platform support

| Feature | Windows | Linux |
|---------|---------|-------|
| Voice companion (push-to-talk) | Yes | Yes |
| Screen capture + vision | Yes | Yes |
| Pointing overlay (cursor buddy) | Yes | Yes |
| UI element snapping | UIA tree | AT-SPI2 |
| Computer Use (click/type/launch) | Yes | Yes |
| System tray integration | Yes | Yes |
| .exe / Setup installer | Yes | — |
| .deb package | — | Yes |
| AppImage | — | Yes |

---

## Building from source

### Linux

```bash
# Install build dependencies
make install-deps

# Build everything (portable + AppImage + .deb)
make all-linux

# Or individual targets
make build-linux    # Portable binary in dist/Glance/
make appimage       # AppImage
make deb            # .deb package
```

Requires: Python 3.10+, pip, dpkg-deb (for .deb), FUSE + wget (for AppImage).

### Windows

```powershell
# From repo root
build.bat              # Portable build → dist\Glance\Glance.exe
build.bat installer    # + Inno Setup installer → dist\Setup-Glance.exe
```

Requires: Python 3.10+, pip. Inno Setup 6 for the installer (optional).

### Icons

Platform icons are generated from `glance.png`:

```bash
python packaging/generate_icons.py
# or: make icons
```

---

## Project layout

```
glance/
  shell/        # Voice + screen companion (the main app)
  agent/        # Computer-use actuation, permission model, safe file ops
  providers/    # Claude / OpenAI / Gemini / Ollama / heuristic
  platform/     # OS-specific backends (Windows UIA, Linux AT-SPI2)
  cli.py        # glance organize / undo / run
packaging/
  generate_icons.py     # Icon generation from glance.png
  glance_app.py         # PyInstaller entry point
  linux/                # Linux-specific build configs
glance.spec             # PyInstaller spec (Windows)
installer.iss           # Inno Setup script (Windows)
build.bat               # Windows build script
Makefile                # Linux build automation
```

---

## Safety

The **file organizer** is move-only and fully reversible (`glance undo`).

The **voice agent acts directly** on your machine — she does what you ask. She stops before genuinely irreversible, high-stakes actions (send, delete, buy). Press **Esc** to cancel at any time. This is an early build acting on your real machine — watch her.

---

## Roadmap

- Learnable skills — teach Glance new routines by voice
- Glance Bridge (MCP) — expose eyes and pointer as an MCP server
- Better desktop control — opt-in shortcut/icon arrangement
- Multi-monitor support improvements
- Mobile companion (status + remote control)

---

## Credits & license

Glance is an independent project by [Anas Abubakar](https://github.com/Anasabubakar). It builds on:

- **Clicky** by [@farzaa](https://github.com/farzaa/clicky) — the original macOS screen-companion concept (MIT)
- **Clicky for Windows** by [Bitshank-2338](https://github.com/Bitshank-2338/clicky-windows) — the Python/PyQt6 Windows companion Glance's voice + pointing pipeline derives from (MIT)
- **OpenClicky** by [@jasonkneen](https://github.com/jasonkneen/openclicky) — the actively maintained open-source Clicky (MIT)

Released under the [MIT License](LICENSE). Not affiliated with or endorsed by the above projects or Anthropic.
