"""filesys.py — open, find, create, move, copy, rename, zip and trash files by name."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from .nlp import fuzzy_pick
from .registry import Result, rule

_KNOWN = {"downloads": "Downloads", "download": "Downloads", "documents": "Documents", "document": "Documents",
          "desktop": "Desktop", "pictures": "Pictures", "photos": "Pictures", "music": "Music", "videos": "Videos",
          "home": "", "my home": ""}
_ROOTS = ("Downloads", "Documents", "Desktop", "Pictures", "Videos", "Music")
_SKIP = {".cache", "node_modules", ".git", "__pycache__", "snap", ".local", ".config", ".npm", "miniconda3", ".nvm"}


def _home(ctx) -> Path:
    return Path(ctx.home)


def known_folder(ctx, name: str, must_exist: bool = True):
    n = re.sub(r"^(?:my|the)\s+", "", name.strip().lower())
    n = re.sub(r"\s+(?:folder|directory)$", "", n)
    if n in _KNOWN:
        p = _home(ctx) / _KNOWN[n] if _KNOWN[n] else _home(ctx)
        return p if (p.is_dir() or not must_exist) else None
    return None


def search(ctx, query: str, kind: str = "any", limit: int = 8, roots=None) -> list:
    """Files/folders whose name matches `query` (case-insensitive, fuzzy), newest first."""
    q = query.strip().lower().strip('"\'')
    base = _home(ctx)
    roots = roots or [base / r for r in _ROOTS if (base / r).is_dir()] + [base]
    hits, seen = [], set()
    for root in roots:
        depth0 = len(root.parts)
        for dirpath, dirs, files in os.walk(root):
            if len(Path(dirpath).parts) - depth0 > 4:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith(".")]
            names = []
            if kind in ("any", "dir"):
                names += [(d, True) for d in dirs]
            if kind in ("any", "file"):
                names += [(f, False) for f in files if not f.startswith(".")]
            for n, is_dir in names:
                low = n.lower()
                stem = low.rsplit(".", 1)[0] if not is_dir else low
                if q == low or q == stem or q in low:
                    p = Path(dirpath) / n
                    if p not in seen:
                        seen.add(p)
                        hits.append(p)
            if len(hits) > 200:
                break
    def score(p):
        n = p.name.lower()
        exact = 0 if q in (n, n.rsplit(".", 1)[0]) else 1
        try:
            return (exact, -p.stat().st_mtime)
        except OSError:
            return (exact, 0)
    return sorted(hits, key=score)[:limit]


def _open(ctx, path: Path):
    ctx.spawn(["xdg-open", str(path)])


def _unique(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem, suf = dest.stem, dest.suffix
    i = 2
    while True:
        cand = dest.with_name(f"{stem} ({i}){suf}")
        if not cand.exists():
            return cand
        i += 1


@rule(r"(?:open|show|go to)\s+(?:up\s+)?(?:the\s+|my\s+)?(?P<f>downloads?|documents?|desktop|pictures|photos|music|videos|home)(?:\s+folder)?$",
      name="open_known_folder", prio=36)
def open_known_folder(ctx, m, text):
    p = known_folder(ctx, m.group("f"))
    if not p:
        return None
    ctx.caption(f"Opening {p.name}", 0.4)
    _open(ctx, p)
    return Result(f"Opening {p.name}.")


@rule(r"(?:open|show|play|view)\s+(?:the\s+|my\s+)?(?:latest|newest|last|most recent|recent)\s+(?P<k>download|screenshot|file|photo|picture|document|video|pdf|recording)s?$",
      name="open_latest", prio=37)
def open_latest(ctx, m, text):
    k = m.group("k")
    base = _home(ctx)
    d = {"download": "Downloads", "screenshot": "Pictures", "photo": "Pictures", "picture": "Pictures",
         "document": "Documents", "video": "Videos", "recording": "Videos"}.get(k, "Downloads")
    exts = {"pdf": (".pdf",), "photo": (".jpg", ".jpeg", ".png", ".heic", ".webp"), "picture": (".jpg", ".jpeg", ".png", ".webp"),
            "screenshot": (".png",), "video": (".mp4", ".mkv", ".webm", ".mov"), "recording": (".mp4", ".mkv", ".webm", ".mov")}.get(k)
    folder = base / d
    if not folder.is_dir():
        return None
    files = [p for p in folder.rglob("*") if p.is_file() and not p.name.startswith(".")
             and (exts is None or p.suffix.lower() in exts)
             and (k != "screenshot" or "screenshot" in p.name.lower() or "glance" in p.name.lower())]
    if not files:
        return Result(f"I couldn't find a recent {k}.", ok=False)
    newest = max(files, key=lambda p: p.stat().st_mtime)
    ctx.caption(f"Opening {newest.name[:30]}", 0.5)
    _open(ctx, newest)
    return Result(f"Opening {newest.name}.")


@rule(r"(?:open|show|play|view|find|where(?:'s| is))\s+(?:the\s+|my\s+)?(?:file\s+|document\s+)?(?:called\s+|named\s+)?(?P<n>[\w .\-()]+\.\w{2,5})$",
      name="open_file", prio=38)
def open_file(ctx, m, text):
    hits = search(ctx, m.group("n"), "file", 5)
    if not hits:
        if re.search(r"\.(com|org|net|io|dev|app|co|ai|me|edu|gov|info|xyz|tv|ly)$", m.group("n").strip(), re.I):
            return None                          # a website, not a file
        return Result(f"I couldn't find {m.group('n')}.", ok=False)
    ctx.caption(f"Opening {hits[0].name[:30]}", 0.5)
    _open(ctx, hits[0])
    return Result(f"Opening {hits[0].name}.")


@rule(r"(?:open|show|go to)\s+(?:the\s+|my\s+)?(?P<n>[\w .\-()]{2,40}?)\s+(?:folder|directory)(?:\s+(?:in|on|inside|from)\s+(?:my\s+|the\s+)?(?P<w>[\w ]+))?$",
      name="open_folder_named", prio=38)
def open_folder_named(ctx, m, text):
    k = known_folder(ctx, m.group("n"))
    if k:
        _open(ctx, k)
        return Result(f"Opening {k.name}.")
    roots = None
    if m.group("w"):
        w = known_folder(ctx, m.group("w"))
        roots = [w] if w else None
    hits = search(ctx, m.group("n"), "dir", 3, roots)
    if not hits:
        return Result(f"I couldn't find a folder called {m.group('n')}.", ok=False)
    _open(ctx, hits[0])
    return Result(f"Opening {hits[0].name}.")


@rule(r"(?:find|search for|look for|where(?:'s| is| are))\s+(?:my\s+|the\s+)?(?:files?|documents?|folders?)?\s*(?:called\s+|named\s+)?(?P<n>[\w .\-()]{2,40})$",
      name="find_files", prio=71)
def find_files(ctx, m, text):
    if not re.search(r"\b(file|folder|document|pdf|photo|picture)s?\b", text):
        return None
    hits = search(ctx, m.group("n"), "any", 6)
    if not hits:
        return Result(f"I couldn't find anything called {m.group('n')}.", ok=False)
    if len(hits) == 1:
        _open(ctx, hits[0])
        return Result(f"Found {hits[0].name} in {hits[0].parent.name}. Opening it.")
    _open(ctx, hits[0].parent)
    names = ", ".join(h.name for h in hits[:3])
    return Result(f"I found {len(hits)} matches, like {names}. Opening the folder of the first.")


def _resolve_dir(ctx, name: str):
    k = known_folder(ctx, name, must_exist=False)
    if k:
        return k
    hits = search(ctx, name, "dir", 1)
    return hits[0] if hits else None


@rule(r"(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+|named\s+)?(?P<n>[\w .\-()]{1,40}?)(?:\s+(?:in|on|inside|under)\s+(?:my\s+|the\s+)?(?P<w>[\w ]+))?$",
      name="make_folder", prio=52)
def make_folder(ctx, m, text):
    parent = _resolve_dir(ctx, m.group("w")) if m.group("w") else _home(ctx) / "Desktop"
    if parent is None:
        return Result(f"I couldn't find {m.group('w')}.", ok=False)
    p = _unique(parent / m.group("n").strip())
    p.mkdir(parents=True, exist_ok=True)
    return Result(f"Created the folder {p.name} in {parent.name}.")


@rule(r"(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?(?:text\s+|empty\s+)?file\s+(?:called\s+|named\s+)?(?P<n>[\w .\-()]{1,40}?)(?:\s+(?:in|on|inside|under)\s+(?:my\s+|the\s+)?(?P<w>[\w ]+))?$",
      name="make_file", prio=52)
def make_file(ctx, m, text):
    parent = _resolve_dir(ctx, m.group("w")) if m.group("w") else _home(ctx) / "Desktop"
    if parent is None:
        return Result(f"I couldn't find {m.group('w')}.", ok=False)
    name = m.group("n").strip()
    if "." not in name:
        name += ".txt"
    parent.mkdir(parents=True, exist_ok=True)
    p = _unique(parent / name)
    p.touch()
    return Result(f"Created {p.name} in {parent.name}.")


def _one(ctx, name: str):
    hits = search(ctx, name, "any", 3)
    if not hits:
        return None, f"I couldn't find {name}."
    exact = [h for h in hits if name.lower().strip() in (h.name.lower(), h.stem.lower())]
    return (exact[0] if exact else hits[0]), None


@rule(r"(?P<v>move|copy)\s+(?:the\s+|my\s+)?(?:file\s+|folder\s+)?(?P<n>[\w .\-()]{2,40}?)\s+(?:to|into|in)\s+(?:the\s+|my\s+)?(?P<d>[\w .\-]{2,30}?)(?:\s+folder)?$",
      name="move_copy", prio=53)
def move_copy(ctx, m, text):
    src, err = _one(ctx, m.group("n"))
    if err:
        return Result(err, ok=False)
    dest = _resolve_dir(ctx, m.group("d"))
    if dest is None:
        return Result(f"I couldn't find the folder {m.group('d')}.", ok=False)
    target = _unique(dest / src.name)
    if m.group("v") == "move":
        shutil.move(str(src), str(target))
        return Result(f"Moved {src.name} to {dest.name}.")
    if src.is_dir():
        shutil.copytree(src, target)
    else:
        shutil.copy2(src, target)
    return Result(f"Copied {src.name} to {dest.name}.")


@rule(r"rename\s+(?:the\s+|my\s+)?(?:file\s+|folder\s+)?(?P<a>[\w .\-()]{2,40}?)\s+(?:to|as)\s+(?P<b>[\w .\-()]{1,40})$", name="rename", prio=53)
def rename(ctx, m, text):
    src, err = _one(ctx, m.group("a"))
    if err:
        return Result(err, ok=False)
    new = m.group("b").strip()
    if "." not in new and src.suffix and src.is_file():
        new += src.suffix
    target = _unique(src.with_name(new))
    src.rename(target)
    return Result(f"Renamed it to {target.name}.")


@rule(r"(?:delete|trash|remove|throw away|get rid of)\s+(?:the\s+|my\s+)?(?:file\s+|folder\s+)?(?P<n>[\w .\-()]{2,40})$", name="trash_file", prio=54)
def trash_file(ctx, m, text):
    if re.search(r"\b(tab|window|app|text|word|line|everything|all)\b", m.group("n")):
        return None
    src, err = _one(ctx, m.group("n"))
    if err:
        return None
    if not ctx.confirm(f"move {src.name} to the trash"):
        return Result("Okay, I left it alone.", ok=False)
    rc, _ = ctx.run(["gio", "trash", str(src)])
    return Result(f"Moved {src.name} to the trash.", ok=rc == 0)


@rule(r"empty\s+(?:the\s+|my\s+)?trash$|empty the recycle bin$", name="empty_trash", prio=54)
def empty_trash(ctx, m, text):
    if not ctx.confirm("permanently empty the trash"):
        return Result("Okay, I left the trash alone.", ok=False)
    ctx.run(["gio", "trash", "--empty"])
    return Result("Emptied the trash.")


@rule(r"(?:open|show)\s+(?:the\s+|my\s+)?(?:trash|recycle bin|wastebasket)$", name="open_trash", prio=36)
def open_trash(ctx, m, text):
    ctx.spawn(["xdg-open", "trash:///"])
    return Result("")


@rule(r"(?:zip|compress|archive)\s+(?:up\s+)?(?:the\s+|my\s+)?(?:file\s+|folder\s+)?(?P<n>[\w .\-()]{2,40})$", name="zip", prio=55)
def zip_it(ctx, m, text):
    src, err = _one(ctx, m.group("n"))
    if err:
        return Result(err, ok=False)
    base = _unique(src.parent / src.name)
    if src.is_dir():
        out = shutil.make_archive(str(base), "zip", root_dir=str(src.parent), base_dir=src.name)
    else:
        out = shutil.make_archive(str(base), "zip", root_dir=str(src.parent), base_dir=src.name)
    return Result(f"Made {Path(out).name}.")


@rule(r"how (?:big|large) is\s+(?:the\s+|my\s+)?(?:file\s+|folder\s+)?(?P<n>[\w .\-()]{2,40})$|how much space (?:does|is)\s+(?P<n2>[\w .\-()]{2,40})\s+(?:take|using|use)$",
      name="size_of", prio=56)
def size_of(ctx, m, text):
    name = m.group("n") or m.group("n2")
    src, err = _one(ctx, name)
    if err:
        return Result(err, ok=False)
    total = src.stat().st_size if src.is_file() else sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
    for unit in ("bytes", "KB", "MB", "GB"):
        if total < 1024 or unit == "GB":
            return Result(f"{src.name} is {total:.0f} {unit}." if unit == "bytes" else f"{src.name} is {total:.1f} {unit}.")
        total /= 1024
    return None
