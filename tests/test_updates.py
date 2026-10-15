"""Update comparison must not call an OLDER release an update."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import pytest  # noqa: E402

pytest.importorskip("PyQt6")
from ui.launcher.pages.updates import clean_notes, is_newer  # noqa: E402


def test_is_newer_numeric_not_string():
    assert is_newer("v0.3.10", "0.3.9")          # string compare would say no
    assert is_newer("0.4.0", "0.3.99")
    assert not is_newer("v0.3.5", "0.3.6")       # older release is NOT an update
    assert not is_newer("0.3.6", "v0.3.6")


def test_clean_notes_strips_markdown():
    t = clean_notes("## Fix\n\n- **Bold** and `code`")
    assert "#" not in t and "**" not in t and "`" not in t
