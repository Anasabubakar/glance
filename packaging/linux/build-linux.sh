#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# Glance for Linux — build script
#
# Produces:
#   dist/Glance/                    — portable folder
#   dist/Glance-VERSION-x86_64.AppImage — AppImage
#   dist/glance_VERSION_ARCH.deb    — Debian/Ubuntu package
#
# Usage:
#   ./packaging/linux/build-linux.sh              (portable only)
#   ./packaging/linux/build-linux.sh appimage     (+ AppImage)
#   ./packaging/linux/build-linux.sh deb          (+ .deb)
#   ./packaging/linux/build-linux.sh all          (everything)
# ────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

VERSION=$(python3 -c "import glance; print(glance.__version__)")
ARCH=$(dpkg --print-architecture 2>/dev/null || echo "amd64")

echo ""
echo "================================================================"
echo "  Glance v${VERSION} for Linux — Build"
echo "================================================================"
echo ""

# ── Build the portable folder if it doesn't exist yet ────────────────
build_portable() {
    # 1. Generate icons if missing
    if [ ! -f "packaging/icons/glance-256.png" ]; then
        echo "[1/5] Generating icons..."
        python3 packaging/generate_icons.py
    else
        echo "[1/5] Icons already generated."
    fi

    # 2. Install build deps if missing
    echo "[2/5] Checking build dependencies..."
    python3 -c "import PyInstaller" 2>/dev/null || {
        echo "    Installing PyInstaller..."
        pip install --quiet --upgrade pyinstaller
    }
    python3 -c "import PyQt6" 2>/dev/null || {
        echo "    Installing project requirements..."
        pip install --quiet -e ".[shell,claude,openai,gemini]"
    }
    # Ensure all provider SDKs are present even if PyQt6 was already installed —
    # otherwise PyInstaller collect_all() silently skips them and the packaged
    # build can't switch to OpenAI/Gemini at runtime.
    python3 -c "import openai" 2>/dev/null || {
        echo "    Installing openai..."
        pip install --quiet "openai>=1.0"
    }
    python3 -c "import google.generativeai" 2>/dev/null || {
        echo "    Installing google-generativeai..."
        pip install --quiet "google-generativeai>=0.8"
    }

    # 3. Clean old build
    echo "[3/5] Cleaning old build..."
    rm -rf build/ dist/

    # 4. Run PyInstaller
    echo "[4/5] Building with PyInstaller (this takes 2-5 min)..."
    python3 -m PyInstaller packaging/linux/glance-linux.spec --clean --noconfirm

    # 4b. Fix libexpat.so.1 — PyInstaller sometimes collects an older
    # system libexpat under the .so.1 soname alongside the correct
    # Python 3.13 one (libexpat.so.1.11.1). Force the versioned file
    # to overwrite the soname link in every location it appears.
    echo "[4b/5] Repairing libexpat.so.1 (Python 3.13 compat)..."
    NEWEST_EXPAT=$(find dist/Glance/_internal -name 'libexpat.so.1.*' -type f 2>/dev/null | sort | tail -1)
    if [ -n "$NEWEST_EXPAT" ] && [ -f "$NEWEST_EXPAT" ]; then
        echo "    Using: $NEWEST_EXPAT"
        find dist/Glance/_internal -name 'libexpat.so.1' | while read -r target; do
            echo "    Overwriting: $target"
            cp -f "$NEWEST_EXPAT" "$target"
        done
    else
        echo "    WARNING: no libexpat.so.1.x found — build may crash on launch"
    fi

    # 5. Bundle extras
    echo "[5/5] Bundling docs and config template..."
    [ -f .env.example ] && cp -f .env.example "dist/Glance/.env.example"
    [ -f LICENSE ] && cp -f LICENSE "dist/Glance/LICENSE"

    echo ""
    echo "================================================================"
    echo "  Portable build complete: dist/Glance/"
    echo "  Run: ./dist/Glance/glance-companion"
    echo "================================================================"
    echo ""
}

# ── AppImage ──────────────────────────────────────────────────────────
build_appimage() {
    if [ ! -d "dist/Glance" ]; then
        echo "[AppImage] dist/Glance/ not found — building portable first..."
        build_portable
    fi

    echo ""
    echo "Building AppImage..."

    APPDIR="dist/Glance.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor"

    cp -a dist/Glance/* "$APPDIR/usr/bin/"

    cp packaging/linux/glance.desktop "$APPDIR/usr/share/applications/glance.desktop"
    cp packaging/linux/glance.desktop "$APPDIR/glance.desktop"

    for size in 16 24 32 48 64 128 256 512; do
        icon_dir="$APPDIR/usr/share/icons/hicolor/${size}x${size}/apps"
        mkdir -p "$icon_dir"
        if [ -f "packaging/icons/glance-${size}.png" ]; then
            cp "packaging/icons/glance-${size}.png" "$icon_dir/glance.png"
        fi
    done
    cp "packaging/icons/glance-256.png" "$APPDIR/glance.png"
    cp "packaging/icons/glance-256.png" "$APPDIR/.DirIcon"

    cat > "$APPDIR/AppRun" << 'APPRUN'
#!/bin/bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/bin:${LD_LIBRARY_PATH:-}"
export APPIMAGE_EXTRACT_AND_RUN=1
cd "${HERE}" || exit 1
exec "${HERE}/usr/bin/glance-companion" "$@"
APPRUN
    chmod +x "$APPDIR/AppRun"

    TOOL="dist/appimagetool-x86_64.AppImage"
    if [ ! -f "$TOOL" ]; then
        echo "  Downloading appimagetool..."
        wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$TOOL"
        chmod +x "$TOOL"
    fi

    ARCH=x86_64 "$TOOL" --no-appstream "$APPDIR" "dist/Glance-${VERSION}-x86_64.AppImage"
    rm -f "$TOOL"
    echo "  AppImage: dist/Glance-${VERSION}-x86_64.AppImage"
}

# ── .deb ──────────────────────────────────────────────────────────────
build_deb() {
    if [ ! -d "dist/Glance" ]; then
        echo "[deb] dist/Glance/ not found — building portable first..."
        build_portable
    fi

    echo ""
    echo "Building .deb package..."

    DEB_ROOT="dist/deb-build"
    rm -rf "$DEB_ROOT"

    INSTALL_DIR="$DEB_ROOT/opt/glance"
    mkdir -p "$INSTALL_DIR"
    cp -a dist/Glance/* "$INSTALL_DIR/"

    mkdir -p "$DEB_ROOT/usr/bin"
    cat > "$DEB_ROOT/usr/bin/glance-companion" << 'LAUNCHER'
#!/bin/bash
exec /opt/glance/glance-companion "$@"
LAUNCHER
    chmod +x "$DEB_ROOT/usr/bin/glance-companion"

    mkdir -p "$DEB_ROOT/usr/share/applications"
    cp packaging/linux/glance.desktop "$DEB_ROOT/usr/share/applications/glance.desktop"

    for size in 16 24 32 48 64 128 256 512; do
        icon_dir="$DEB_ROOT/usr/share/icons/hicolor/${size}x${size}/apps"
        mkdir -p "$icon_dir"
        if [ -f "packaging/icons/glance-${size}.png" ]; then
            cp "packaging/icons/glance-${size}.png" "$icon_dir/glance.png"
        fi
    done

    mkdir -p "$DEB_ROOT/usr/share/metainfo"
    cp packaging/linux/glance.metainfo.xml "$DEB_ROOT/usr/share/metainfo/glance.metainfo.xml"

    mkdir -p "$DEB_ROOT/DEBIAN"
    INSTALLED_SIZE=$(du -sk "$DEB_ROOT" | cut -f1)
    cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: glance
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: Anas Abubakar <anas@glance.dev>
Homepage: https://github.com/Anasabubakar/glance
Description: Open-source AI desktop companion
 Glance sees your screen, points at things, and acts on them.
 Voice-controlled AI assistant with screen understanding,
 multiple LLM providers (Claude, OpenAI, Gemini, Ollama),
 and desktop integration.
Depends: libgl1, libegl1, libxkbcommon0, libdbus-1-3, libfontconfig1,
 libxcb-cursor0, libglib2.0-0, libpulse0, libasound2, libxcb-xinerama0,
 libxcb-xfixes0, libxcb-shape0, libxkbcommon-x11-0
Recommends: ollama
Suggests: portaudio19-dev
EOF

    cat > "$DEB_ROOT/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor/ 2>/dev/null || true
fi
POSTINST
    chmod 0755 "$DEB_ROOT/DEBIAN/postinst"

    cat > "$DEB_ROOT/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor/ 2>/dev/null || true
fi
POSTRM
    chmod 0755 "$DEB_ROOT/DEBIAN/postrm"

    find "$DEB_ROOT" -type d -exec chmod 755 {} \;
    find "$DEB_ROOT/opt/glance" -type f -exec chmod 644 {} \;
    find "$DEB_ROOT/opt/glance" -type f -name "glance-companion" -exec chmod 755 {} \;
    find "$DEB_ROOT/opt/glance" -type f -name "*.so*" -exec chmod 755 {} \;
    find "$DEB_ROOT/opt/glance" -type f -name "*.so" -exec chmod 755 {} \;
    find "$DEB_ROOT/opt/glance/_internal" -type f \( -name "python3*" -o -name "*.bin" -o -name "loader" \) -exec chmod 755 {} \; 2>/dev/null || true

    DEB_FILE="dist/glance_${VERSION}_${ARCH}.deb"
    dpkg-deb --build "$DEB_ROOT" "$DEB_FILE"
    echo "  .deb: ${DEB_FILE}"

    rm -rf "$DEB_ROOT"
}

# ── Dispatch ──────────────────────────────────────────────────────────
case "${1:-}" in
    appimage)  build_appimage ;;
    deb)       build_deb ;;
    all)       build_portable; build_appimage; build_deb ;;
    "")        build_portable ;;
    *)         echo "Usage: $0 [appimage|deb|all]"; exit 1 ;;
esac
