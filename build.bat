@echo off
REM ────────────────────────────────────────────────────────────────────
REM Glance Windows — one-click build script
REM
REM Produces:  dist\Glance\Glance.exe   (portable folder)
REM            dist\Setup-Glance.exe    (if Inno Setup is installed)
REM
REM Usage:  build.bat           ← builds portable folder only
REM         build.bat installer ← also builds Setup-Glance.exe
REM
REM Run from the repository root.
REM ────────────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion

REM Auto-detect if we're in glance/shell — if so, go up to root
if exist "..\..\pyproject.toml" (
    cd /d "%~dp0..\.."
) else if exist "pyproject.toml" (
    REM already at root
) else (
    echo [ERROR] Run this from the repo root or from glance\shell\.
    exit /b 1
)

echo.
echo ================================================================
echo   Glance for Windows — Build
echo ================================================================
echo.

REM ── 1. Sanity check Python ─────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH. Install Python 3.11+ first.
    exit /b 1
)

REM ── 2. Install build deps if missing ───────────────────────────────
echo [1/5] Checking build dependencies...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo     Installing PyInstaller...
    python -m pip install --quiet --upgrade pyinstaller
)
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo     Installing project requirements...
    python -m pip install --quiet -e ".[shell,claude]"
)

REM ── 3. Generate icon from logo ─────────────────────────────────────
echo [2/5] Generating icons from glance.png...
if exist "glance.png" (
    python packaging\generate_icons.py
) else (
    echo     [WARN] glance.png not found — using existing icon.ico
)

REM ── 4. Clean old build ─────────────────────────────────────────────
echo [3/5] Cleaning old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ── 5. Run PyInstaller ─────────────────────────────────────────────
echo [4/5] Building with PyInstaller (this takes 2-5 min)...
python -m PyInstaller glance.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. Check the output above.
    exit /b 1
)

REM ── 6. Copy extras into the dist folder ────────────────────────────
echo [5/5] Bundling docs and env template...
if exist ".env.example" copy /y ".env.example" "dist\Glance\.env.example" >nul
if exist "LICENSE"      copy /y "LICENSE"       "dist\Glance\LICENSE"      >nul
if exist "README.md"    copy /y "README.md"     "dist\Glance\README.md"    >nul

echo.
echo ================================================================
echo   Portable build complete!
echo   Run:  dist\Glance\Glance.exe
echo ================================================================
echo.

REM ── 7. Optional: build Inno Setup installer ────────────────────────
if /i "%1"=="installer" (
    echo Building Inno Setup installer...
    where iscc >nul 2>&1
    if errorlevel 1 (
        set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        if not exist "!ISCC!" (
            echo [WARN] Inno Setup not found. Install from https://jrsoftware.org/isdl.php
            echo        Then re-run:  build.bat installer
            exit /b 0
        )
        "!ISCC!" installer.iss
    ) else (
        iscc installer.iss
    )
    echo.
    echo Installer: dist\Setup-Glance.exe
)

endlocal
