"""Deterministic 'open the X folder' shortcut."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

from fastpath import find_folder, parse_open_folder  # noqa: E402


def test_parse():
    assert parse_open_folder("open the projects folder") == ("projects", None)
    assert parse_open_folder("Open projects folder on my desktop.") == ("projects", "desktop")
    assert parse_open_folder("open my downloads folder") == ("downloads", None)
    assert parse_open_folder("open youtube") is None
    assert parse_open_folder("click on send prompt") is None


def test_find_case_insensitive_and_nested(tmp_path):
    (tmp_path / "Desktop" / "Projects").mkdir(parents=True)
    (tmp_path / "Desktop" / "Stuff" / "Deep").mkdir(parents=True)
    (tmp_path / "Downloads").mkdir()
    assert find_folder("projects", home=tmp_path) == tmp_path / "Desktop" / "Projects"
    assert find_folder("projects", "desktop", home=tmp_path) == tmp_path / "Desktop" / "Projects"
    assert find_folder("deep", home=tmp_path) == tmp_path / "Desktop" / "Stuff" / "Deep"
    assert find_folder("downloads", home=tmp_path) == tmp_path / "Downloads"
    assert find_folder("home", home=tmp_path) == tmp_path
    assert find_folder("nope", home=tmp_path) is None


def test_real_machine_projects_folder_resolves_when_present():
    from pathlib import Path
    p = Path.home() / "Desktop" / "Projects"
    if p.is_dir():
        assert find_folder("projects") == p
