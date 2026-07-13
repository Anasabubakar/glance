# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the Glance voice companion (Linux).
# Build:  cd <repo-root> && python -m PyInstaller packaging/linux/glance-linux.spec
# Output: dist/Glance/glance-companion  (folder build).

import os
import sys
import ctypes.util
import glob

# ── Compute repo root from this spec file's location ──────────────────
# SPECPATH is set by PyInstaller to the directory containing this .spec file.
ROOT = os.path.normpath(os.path.join(SPECPATH, '..', '..'))

sys.path.insert(0, os.path.join(ROOT, "glance", "shell"))

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# ── Bundle the correct libexpat for Python 3.13 ──────────────────────
# Python 3.13's pyexpat.so needs XML_SetAllocTrackerActivationThreshold
# (expat >= 2.6.3), which is newer than what most Linux distros ship
# system-wide. Bundle the exact libexpat that this Python was built
# against, placed next to pyexpat.so so the dynamic linker finds it first.
def _find_libexpat():
    candidates = [
        os.path.join(sys.prefix, "lib", "libexpat.so.1"),
        os.path.join(sys.exec_prefix, "lib", "libexpat.so.1"),
        "/usr/lib/x86_64-linux-gnu/libexpat.so.1",
        "/lib/x86_64-linux-gnu/libexpat.so.1",
    ]
    for pattern in (
        os.path.join(sys.prefix, "lib", "libexpat.so.1*"),
        "/usr/lib/x86_64-linux-gnu/libexpat.so.1*",
    ):
        candidates.extend(sorted(glob.glob(pattern)))
    for c in candidates:
        if os.path.isfile(c) or os.path.islink(c):
            return os.path.realpath(c)
    name = ctypes.util.find_library("expat")
    return name

_expat = _find_libexpat()
if _expat:
    # Place BOTH next to pyexpat.so (python3.13/lib-dynload/) AND at the
    # bundle root so both search paths resolve to the correct version.
    print(f"[glance-linux.spec] Bundling libexpat: {_expat}")
    binaries.append((_expat, "python3.13/lib-dynload"))
    binaries.append((_expat, "."))
else:
    print("[glance-linux.spec] WARNING: libexpat not found — build may not run")

# Third-party packages — data, shared libs, submodules.
for pkg in (
    "PyQt6", "sounddevice", "soundfile",
    "edge_tts", "faster_whisper", "av", "mss",
    # Multi-provider LLM SDKs — all optional at runtime, but bundled so users
    # can pick ANY provider from the tray without a separate install.
    "anthropic", "openai", "google", "google.generativeai",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception as e:
        print(f"[glance-linux.spec] collect_all({pkg}) skipped: {e}")

# The shell's bare-name top-level modules + packages.
hiddenimports += [
    "config", "main", "companion_manager", "hotkey",
    "memory_store", "google_workspace",
    "keyboard", "pynput", "dotenv",
]
for pkg in ("ai", "audio", "ui", "screen", "skills", "tutor_features"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception as e:
        print(f"[glance-linux.spec] collect_submodules({pkg}) skipped: {e}")
hiddenimports += collect_submodules("glance")

# Runtime data — all paths relative to repo root
datas += [
    (os.path.join(ROOT, "glance", "shell", "SOUL.md"), "."),
    (os.path.join(ROOT, "glance", "shell", "skills"),  "skills"),
    (os.path.join(ROOT, "glance", "shell", "assets"),  "assets"),
]

a = Analysis(
    [os.path.join(ROOT, "packaging", "glance_app.py")],
    pathex=[ROOT, os.path.join(ROOT, "glance", "shell")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[os.path.join(SPECPATH, "rthook_expat.py")],
    excludes=[
        "tkinter",
        "tensorflow", "tensorboard", "keras",
        "torch", "torchvision", "torchaudio",
        "jax", "jaxlib",
        "transformers", "sklearn", "scikit-learn",
        "pandas", "matplotlib", "scipy",
        "botocore", "boto3", "grpc",
        "llvmlite", "numba", "imageio_ffmpeg",
        "yt_dlp",
        # Windows-only
        "uiautomation", "comtypes",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="glance-companion",
    console=False,
    icon=os.path.join(ROOT, "packaging", "icons", "glance-256.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,           # do NOT strip — Python 3.13 libexpat symbols get broken
    upx=False,
    name="Glance",
)
