"""Runtime hook: preload libexpat so pyexpat finds the correct symbols."""
import ctypes
import os
import sys
import glob

def _preload():
    base = os.path.join(sys._MEIPASS, "_internal") if hasattr(sys, "_MEIPASS") else ""
    if not base:
        base = os.path.dirname(sys.executable)

    for search in (base, os.path.join(base, ".."), sys._MEIPASS if hasattr(sys, "_MEIPASS") else ""):
        if not search:
            continue
        for pat in ("libexpat.so*", "libexpat.so.1*"):
            hits = glob.glob(os.path.join(search, pat))
            if hits:
                try:
                    ctypes.CDLL(hits[0], mode=ctypes.RTLD_GLOBAL)
                    return
                except OSError:
                    pass

_preload()
