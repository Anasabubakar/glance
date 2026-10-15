"""
frozen_env.py — keep child processes away from the PyInstaller bundle's libraries.

The installed app sets LD_LIBRARY_PATH to its own bundled glib/gio. Every program
Glance launches inherits it: the system `gdbus` (screen capture, clicks, typing) and
the apps it opens then crash with "undefined symbol", so they silently did nothing.
Call install() once at startup; it makes subprocess.Popen default to a clean env.
"""

import os
import subprocess
import sys


def clean_env(env=None) -> dict:
    out = dict(os.environ if env is None else env)
    if "LD_LIBRARY_PATH_ORIG" in out:
        out["LD_LIBRARY_PATH"] = out.pop("LD_LIBRARY_PATH_ORIG")
    else:
        out.pop("LD_LIBRARY_PATH", None)
    return out


def install() -> None:
    if not (getattr(sys, "frozen", False) and sys.platform.startswith("linux")):
        return
    if getattr(subprocess.Popen, "_glance_clean", False):
        return
    orig = subprocess.Popen.__init__

    def init(self, *a, **kw):
        if kw.get("env") is None:
            kw["env"] = clean_env()
        orig(self, *a, **kw)

    subprocess.Popen.__init__ = init
    subprocess.Popen._glance_clean = True
