"""
Generate all platform icons from the source glance.png logo.

Produces:
  packaging/icons/glance.ico          — Windows (multi-resolution)
  packaging/icons/glance-{N}.png      — Linux (16..512)
  packaging/icons/glance-1024.png     — Full resolution source
  glance/shell/assets/icon.ico        — Copy for PyInstaller spec

Usage:  python packaging/generate_icons.py
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "glance.png"
OUT_DIR = ROOT / "packaging" / "icons"
SHELL_ICO = ROOT / "glance" / "shell" / "assets" / "icon.ico"

LINUX_SIZES = [16, 24, 32, 48, 64, 128, 256, 512]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    src = Image.open(SRC).convert("RGBA")
    print(f"Source: {SRC} ({src.size[0]}x{src.size[1]}, {src.mode})")

    # Linux PNGs
    for size in LINUX_SIZES:
        resized = src.resize((size, size), Image.LANCZOS)
        out = OUT_DIR / f"glance-{size}.png"
        resized.save(out, format="PNG")
        print(f"  {out.name}")

    # Full-res copy
    full = OUT_DIR / "glance-1024.png"
    src_1024 = src.resize((1024, 1024), Image.LANCZOS) if max(src.size) != 1024 else src
    src_1024.save(full, format="PNG")
    print(f"  {full.name}")

    # Windows .ico (multi-resolution)
    # PIL's ICO writer builds all sizes from the largest source, so pass
    # the highest-res image and let the sizes= list drive rescaling.
    ico_path = OUT_DIR / "glance.ico"
    src_512 = src.resize((512, 512), Image.LANCZOS) if max(src.size) != 512 else src
    src_512.save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"  {ico_path.name}")

    # Copy .ico to shell assets (PyInstaller expects it there)
    SHELL_ICO.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(ico_path, SHELL_ICO)
    print(f"  -> {SHELL_ICO.relative_to(ROOT)}")

    print(f"\nDone — {len(LINUX_SIZES)} PNGs + 1 ICO")


if __name__ == "__main__":
    main()
