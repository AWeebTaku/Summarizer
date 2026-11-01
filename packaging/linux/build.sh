#!/usr/bin/env bash
# Make every Linux download from the frozen app in dist/Summarizer.
# Usage: VERSION=2.0.0 NFPM=/path/to/nfpm APPIMAGETOOL=/path/to/appimagetool packaging/linux/build.sh
# Output: release/Summarizer-amd64.deb, -x86_64.rpm, -x86_64.pkg.tar.zst, -x86_64.AppImage
set -euo pipefail
cd "$(dirname "$0")/../.."
: "${VERSION:?set VERSION, for example 2.0.0}"
NFPM="${NFPM:-nfpm}"
APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"
[ -x dist/Summarizer/Summarizer ] || { echo "dist/Summarizer/Summarizer not found: run packaging/build_bundle.py first" >&2; exit 1; }

# Slim the bundle: Qt's translations for other languages and the QML tree are not used by this app.
Q=dist/Summarizer/_internal/PyQt6/Qt6
if [ -d "$Q" ]; then
  find "$Q/translations" -maxdepth 1 -name '*.qm' -delete 2>/dev/null || true
  find "$Q/translations/qtwebengine_locales" -name '*.pak' ! -name 'en-US.pak' -delete 2>/dev/null || true
  rm -rf "$Q/qml"
  rm -f "$Q"/lib/libQt6Quick3D* "$Q"/lib/libQt6QuickControls2* "$Q"/lib/libQt6QuickDialogs2* \
        "$Q"/lib/libQt6QuickTemplates2* "$Q"/lib/libQt6QuickLayouts* "$Q"/lib/libQt6ShaderTools* 2>/dev/null || true
fi

# The graphics stack has to match the machine's drivers, so use the system's libgbm, not the build machine's copy.
rm -f dist/Summarizer/_internal/libgbm.so* dist/Summarizer/_internal/libwayland-server.so*
# Likewise the C++ runtime. The build machine (Ubuntu 22.04) has an old libstdc++; carrying it breaks the graphics
# drivers of newer distributions, which are built against a newer one ("Could not initialize GLX" at startup).
# libstdc++ and libgcc_s are backwards compatible, so the system's copy is always safe to use.
rm -f dist/Summarizer/_internal/libstdc++.so* dist/Summarizer/_internal/libgcc_s.so*

mkdir -p release
export VERSION
"$NFPM" package -f packaging/linux/nfpm.yaml -p deb       -t release/Summarizer-amd64.deb
"$NFPM" package -f packaging/linux/nfpm.yaml -p rpm       -t release/Summarizer-x86_64.rpm
"$NFPM" package -f packaging/linux/nfpm.yaml -p archlinux -t release/Summarizer-x86_64.pkg.tar.zst

# AppImage: the same bundle plus the files an AppImage needs at its root.
APPDIR=build/AppDir
rm -rf "$APPDIR"; mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/bin"
cp -a dist/Summarizer "$APPDIR/usr/lib/summarizer"
ln -s ../lib/summarizer/Summarizer "$APPDIR/usr/bin/summarizer-app"
cp packaging/linux/summarizer.desktop "$APPDIR/summarizer.desktop"
cp packaging/icons/256.png "$APPDIR/summarizer.png"
ln -s summarizer.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/summarizer-app" "$@"
RUN
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run --comp zstd "$APPDIR" release/Summarizer-x86_64.AppImage
ls -lh release
