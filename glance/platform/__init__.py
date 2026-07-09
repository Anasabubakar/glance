"""
glance.platform — OS-specific backends behind one interface.

Every function in this module works on both Windows and Linux. Import from
here instead of reaching for ctypes.windll, comtypes, uiautomation, or
os.startfile directly.
"""
from __future__ import annotations

import sys

_IS_WINDOWS = sys.platform == "win32"
_IS_LINUX = sys.platform.startswith("linux")

if _IS_WINDOWS:
    from glance.platform._windows import (
        open_path,
        detached_popen,
        get_dpi_scale,
        active_window_title,
        tidy_desktop_icons,
        snap_to_element,
        find_ui_element,
        APP_LAUNCHERS,
        launch_app,
    )
elif _IS_LINUX:
    from glance.platform._linux import (
        open_path,
        detached_popen,
        get_dpi_scale,
        active_window_title,
        tidy_desktop_icons,
        snap_to_element,
        find_ui_element,
        APP_LAUNCHERS,
        launch_app,
    )
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
