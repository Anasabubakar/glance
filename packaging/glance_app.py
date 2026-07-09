"""
PyInstaller entry point for the Glance .exe.

Double-clicking the built Glance.exe runs this, which launches the voice
companion (equivalent to `glance run`). Keys are read from the user config dir
(%LOCALAPPDATA%\\Glance\\.env) when frozen — see glance/shell/config.py — so
users just add their keys, no code checkout needed.
"""

import sys

from glance.companion import launch

if __name__ == "__main__":
    raise SystemExit(launch())
