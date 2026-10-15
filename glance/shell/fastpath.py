"""
Deterministic shortcuts for trivial desktop requests, so "open the Projects
folder" never depends on a language model getting a path (or its capitalisation)
right. Pure functions; the caller does the actual opening.
"""

import re
from pathlib import Path
from typing import Iterable, Optional

_OPEN_FOLDER = re.compile(
    r"\bopen\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<name>[\w .&'-]+?)\s+(?:folder|directory)\b"
    r"(?:\s+(?:on|in|from)\s+(?:my\s+|the\s+)?(?P<where>[\w ]+?))?\s*[.!?]?\s*$",
    re.I)

_KNOWN = {"home": "", "downloads": "Downloads", "documents": "Documents",
          "desktop": "Desktop", "pictures": "Pictures", "music": "Music",
          "videos": "Videos", "downloads folder": "Downloads"}


def parse_open_folder(text: str) -> Optional[tuple]:
    """'open the projects folder on my desktop' -> ('projects', 'desktop')."""
    m = _OPEN_FOLDER.search(text.strip())
    if not m:
        return None
    return m.group("name").strip().lower(), (m.group("where") or "").strip().lower() or None


def _roots(home: Path) -> list:
    base = [home, home / "Desktop", home / "Documents", home / "Downloads",
            home / "Pictures", home / "Music", home / "Videos"]
    return [p for p in base if p.is_dir()]


def find_folder(name: str, where: Optional[str] = None, home: Optional[Path] = None,
                roots: Optional[Iterable[Path]] = None) -> Optional[Path]:
    """Find a directory called `name` (case-insensitive). Looks at well-known
    folders and one level beneath them; `where` ('desktop', 'documents', ...)
    narrows it. Returns None if nothing matches."""
    home = home or Path.home()
    name = name.strip().lower()
    if name in ("home",):
        return home
    if name in _KNOWN and _KNOWN[name] and (home / _KNOWN[name]).is_dir():
        return home / _KNOWN[name]
    search = list(roots) if roots is not None else _roots(home)
    if where:
        narrowed = [r for r in search if r.name.lower() == where.lower()]
        search = narrowed or search
    for r in search:                                   # depth 0: the root itself
        if r.name.lower() == name:
            return r
    for r in search:                                   # depth 1: its children
        try:
            for child in sorted(r.iterdir()):
                if child.is_dir() and child.name.lower() == name:
                    return child
        except OSError:
            continue
    for r in search:                                   # depth 2 (e.g. Desktop/x/Projects)
        try:
            for child in sorted(r.iterdir()):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                for sub in sorted(child.iterdir()):
                    if sub.is_dir() and sub.name.lower() == name:
                        return sub
        except OSError:
            continue
    return None
