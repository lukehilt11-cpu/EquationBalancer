#!/usr/bin/env bash
# macOS: build -> extract .app -> delete build/dist -> install to Applications
# Usage: ./build.sh            (builds and installs)
#        ./build.sh --no-install
# (Inno Setup is Windows-only, so on macOS "install" = copy into Applications.)
set -euo pipefail
cd "$(dirname "$0")"

APP="EquationBalancer.app"

echo "[1/4] Building with PyInstaller..."
if ! python3 -m PyInstaller --noconfirm --clean --log-level ERROR balance_gui.spec > build.log 2>&1; then
    echo "PyInstaller failed. Log:"; cat build.log; exit 1
fi

echo "[2/4] Extracting product..."
rm -rf out && mkdir out
mv "dist/$APP" out/

echo "[3/4] Cleaning up build and dist..."
rm -rf build dist build.log

# Ad-hoc sign so Gatekeeper/Apple Silicon will run it locally
codesign --force --deep --sign - "out/$APP" >/dev/null 2>&1 || true

if [[ "${1:-}" == "--no-install" ]]; then
    echo "Done. App is in out/$APP"; exit 0
fi

echo "[4/4] Installing..."
DEST="/Applications"
[[ -w "$DEST" ]] || { DEST="$HOME/Applications"; mkdir -p "$DEST"; }
rm -rf "$DEST/$APP"
ditto "out/$APP" "$DEST/$APP"
xattr -dr com.apple.quarantine "$DEST/$APP" 2>/dev/null || true
echo "Installed to $DEST/$APP"
open "$DEST/$APP"
