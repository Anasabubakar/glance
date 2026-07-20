# Windows Build — Verification Checklist

Since Glance targets Windows too but the primary dev host is Linux, this
checklist verifies the Windows build without a Windows machine. Two paths:

1. **GitHub Actions CI** (recommended — fully automated on every push tag)
2. **Manual verification on Windows** (if you have access to a Windows box)

---

## Path 1: GitHub Actions CI

The `.github/workflows/release.yml` workflow builds Windows on every `v*`
tag push. To trigger a test build without cutting a release:

```bash
# From repo root
gh workflow run "Build & Release"
```

Then watch:

```bash
gh run watch
```

Expected outputs (downloadable as artifacts on the run page):

- `windows-packages/Setup-Glance.exe` — the Inno Setup installer
- `windows-packages/Glance/*` — portable folder

**What to check on the CI run:**

- [ ] `pip install -e ".[shell,claude,dev]"` succeeds (no dep-resolution errors)
- [ ] `python packaging/generate_icons.py` produces `glance/shell/assets/icon.ico`
- [ ] `python -m PyInstaller glance.spec --clean --noconfirm` reaches
      `Build complete!` — look for `dist\Glance\Glance.exe` in the log
- [ ] `iscc installer.iss` succeeds and outputs `dist/Setup-Glance.exe`
- [ ] Artifact upload step attaches both `dist/Glance/` and
      `dist/Setup-Glance.exe`

## Path 2: Manual Windows verification

On a Windows 10/11 machine with Python 3.11+ and Inno Setup 6:

```cmd
git clone https://github.com/Anasabubakar/glance
cd glance
build.bat installer
```

**Expected end state:**

- `dist\Glance\Glance.exe` — portable executable
- `dist\Setup-Glance.exe` — signed installer (unsigned by default; sign
  separately if you have a code-signing cert)

**Launch checklist:**

- [ ] Double-clicking `dist\Glance\Glance.exe` shows the tray icon (no
      console window, no immediate crash)
- [ ] Right-click tray → menu appears with Provider / Settings / Quit
- [ ] The setup wizard appears on first launch (offers Ollama install)
- [ ] Panel opens from tray menu; overlay follows cursor
- [ ] Hotkey (default `Alt+Space` or as configured) triggers listening
- [ ] `%LOCALAPPDATA%\Glance\` is created and holds the config

**Installer checklist:**

- [ ] Running `Setup-Glance.exe` launches the Inno Setup wizard
- [ ] Default install dir is `%LOCALAPPDATA%\Programs\Glance` (per-user,
      no admin needed) — LOWEST privileges
- [ ] Optional task "Install Ollama" downloads & installs Ollama silently
- [ ] Start Menu shortcut `Glance` created
- [ ] Optional desktop shortcut created if the task was checked
- [ ] Optional startup shortcut created if the task was checked
- [ ] Uninstaller removes the app cleanly from Programs & Features

## Known Windows-specific concerns

- **PyQt6 DLLs:** `collect_all("PyQt6")` in `glance.spec` pulls in the Qt
  DLLs. If antivirus blocks them, users may need to whitelist `Glance.exe`.
- **`uiautomation` + `comtypes`:** Windows-only accessibility API for
  reading control text. Excluded on Linux; required on Windows for the
  "read this button" feature. Bundled via `collect_all`.
- **Ollama installer:** the optional `[Run]` block downloads
  `https://ollama.com/download/OllamaSetup.exe` from within Inno Setup.
  If the URL changes upstream, update `installer.iss` line ~63.
- **PyInstaller bootloader antivirus false-positives:** common. Users
  reporting "false positive" should be pointed at
  <https://github.com/pyinstaller/pyinstaller/issues/6754>.

## v0.2.0 — Launcher Dashboard

Glance now includes a Desktop Launcher Dashboard (`glance/shell/ui/launcher/`)
that opens before the companion. When building a release:

- The launcher is included automatically via the existing spec files
- The entry point in `packaging/glance_app.py` calls `glance.companion.launch()`
  which shows the dashboard before the companion shell
- Set `GLANCE_NO_LAUNCHER=1` to skip the dashboard and launch directly

## Troubleshooting

If PyInstaller fails on Windows:

1. **Missing modules at runtime:** add to `hiddenimports` in `glance.spec`
2. **Missing data files:** add to `datas`
3. **DLL load failures:** add the package to `collect_all()` list
4. **Bootloader crashes at start:** rebuild with `--noconfirm --clean`
   and verify no antivirus is quarantining `Glance.exe`

If Inno Setup fails:

1. Ensure `dist\Glance\` exists (PyInstaller ran first)
2. Ensure `LICENSE` and `glance\shell\assets\icon.ico` exist at repo root
3. Check the compiler log for missing `Source:` paths
