# Building Glance

Glance ships as a native installer on both Windows and Linux. The tooling is
already wired up — this doc explains how to run it, what it produces, and how
to debug when a build fails.

> **Reality check.** This is a big Qt + audio + Whisper app. A first PyInstaller
> build almost never works in one shot — expect to iterate: build, hit a
> `ModuleNotFoundError` or missing DLL/SO, add it, rebuild. Budget an afternoon.
> The spec files here are a solid starting point, not a guarantee.

---

## Prerequisites

- **Python 3.11+** (3.11 recommended for CI parity; 3.13 works locally)
- **pip** with `pyinstaller` and the project's shell deps installed:
  ```bash
  pip install -e ".[shell,claude,dev]"
  pip install pyinstaller
  ```

**Linux extras (Ubuntu 22.04+):**
```bash
sudo apt-get install -y libgl1-mesa-dev libegl1-mesa-dev libxkbcommon-dev \
                        libdbus-1-dev libfontconfig1-dev libportaudio2 \
                        fuse libfuse2
```

**Windows extras:**
- [Inno Setup 6](https://jrsoftware.org/isdl.php) — for the `.exe` installer
- (Optional) A code-signing certificate — unsigned installers can be flagged by
  Windows SmartScreen and antivirus.

---

## Linux

```bash
# From the repo root
make all-linux
```

Or step-by-step:
```bash
make icons          # generate icons from glance.png (once)
make build-linux    # portable folder → dist/Glance/
make appimage       # → dist/Glance-<VERSION>-x86_64.AppImage
make deb            # → dist/glance_<VERSION>_amd64.deb
```

The shell script under the hood is `packaging/linux/build-linux.sh` — you can
run it directly if `make` isn't available:
```bash
bash packaging/linux/build-linux.sh [portable|appimage|deb|all]
```

**Test:**
```bash
./dist/Glance/glance-companion                 # portable
sudo dpkg -i dist/glance_0.1.0_amd64.deb       # install .deb
glance-companion                               # launch from PATH
./dist/Glance-0.1.0-x86_64.AppImage            # standalone AppImage
```

## Windows

```cmd
REM From the repo root, in a Developer Command Prompt or PowerShell
build.bat            REM builds portable folder in dist\Glance\
build.bat installer  REM also builds dist\Setup-Glance.exe via Inno Setup
```

Under the hood:
1. `python packaging\generate_icons.py` → creates `.ico` from `glance.png`
2. `python -m PyInstaller glance.spec --clean --noconfirm` → `dist\Glance\`
3. `iscc installer.iss` → `dist\Setup-Glance.exe`

See [`WINDOWS_BUILD_CHECKLIST.md`](WINDOWS_BUILD_CHECKLIST.md) for the
verification checklist and what to look for on a fresh install.

## GitHub Actions CI

Pushing a `v*` tag triggers `.github/workflows/release.yml` which builds
both platforms in parallel and drafts a GitHub release with all artifacts
attached:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

You can also run the workflow on demand:
```bash
gh workflow run "Build & Release"
gh run watch
```

Artifacts are always uploaded, even for non-tag runs — inspect them from the
Actions tab before shipping a real release.

---

## How users add their keys (BYOK)

The frozen app can't write into itself, so keys live in a user-writable dir:

| Platform | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\Glance\.env` |
| Linux   | `~/.local/share/Glance/.env` (XDG standard) |

Two ways to populate it:

1. **Setup wizard** — appears on first launch, walks the user through choosing
   a provider (Ollama for free/offline, or Claude/OpenAI/Gemini/Copilot).
2. **Manually** — copy `.env.example` from the install dir and edit:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   GLANCE_ACTIVE_LLM=claude
   ```
   `glance/shell/config.py` reads this dir when frozen — no rebuild needed.

---

## Debugging build failures

### Missing modules at runtime
Add the module name to `hiddenimports` in the spec file for your platform
(`glance.spec` for Windows, `packaging/linux/glance-linux.spec` for Linux)
and rebuild. Common culprits: Qt plugins, `comtypes` (for `uiautomation` on
Windows), audio backends.

### Missing shared libraries (Linux)
The build script already handles the most common gotcha — Python 3.13's
`pyexpat.so` needs `libexpat.so >= 2.6.3`. The build script bundles the
correct one from `sys.prefix/lib` in a post-build step.

If another library breaks similarly, add it to the `binaries` list in the
spec with:
```python
binaries.append((os.path.join(sys.prefix, "lib", "libFOO.so.X"), "."))
```

### `faster_whisper` / `ctranslate2` runtime errors
The wake word uses a local Whisper model. Its native DLLs/SOs come along via
`collect_all("faster_whisper")`. The model itself downloads on first run
(needs network + write access to the user dir). To ship offline, pre-bundle
the model files in the `datas` list.

### Bundle size is too big
The spec files exclude ~1.8 GB of transitive dead weight (tensorflow, torch,
jax, pandas, scipy, etc.). If your build is >600 MB per platform, something
was pulled in that shouldn't have been — check the PyInstaller log for
`INFO: Analyzing hidden import 'X'` lines and add unwanted packages to
the `excludes` list.

### Antivirus false positives (Windows)
Unsigned PyInstaller apps sometimes get flagged. For real distribution,
**code-sign** `Glance.exe` and `Setup-Glance.exe` (a cheap OV cert clears
most of it). See <https://github.com/pyinstaller/pyinstaller/issues/6754>
for the current workaround list.

### Faster iteration
Build with a console so you can see the tracebacks in real time:

```bash
# Linux — edit the spec temporarily: console=True, then build
# Windows
python -m PyInstaller --console --onedir --name Glance packaging/glance_app.py
```

Run the resulting binary from a terminal, read the traceback, fix, repeat.
Flip `console=False` back on for the release build.

---

## Artifact sizes (v0.1.0)

| Platform | Artifact | Approx size |
|---|---|---|
| Linux | `dist/Glance/` (portable folder) | ~660 MB |
| Linux | `Glance-0.1.0-x86_64.AppImage` | 295 MB |
| Linux | `glance_0.1.0_amd64.deb` | 222 MB |
| Windows | `dist/Glance/` (portable folder) | ~500 MB |
| Windows | `Setup-Glance.exe` (installer) | 200–400 MB |
