#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BSCOTCH_DIR="$SCRIPT_DIR/butterscotch"
BSCOTCH_BUILD_DIR="$SCRIPT_DIR/bscotch-build"

echo "==> Building Butterscotch (desktop, sdl2)..."
cd "$BSCOTCH_DIR"

echo "==> Configuring CMake..."
cmake -B build -G Ninja \
    -DPLATFORM=desktop \
    -DDESKTOP_BACKEND=sdl2 \
    -DCMAKE_BUILD_TYPE=Release

echo "==> Running Ninja..."
ninja -C build -v

echo "==> Verifying build output..."
ls -la build/

BINARY="build/butterscotch"
if [[ ! -f "$BINARY" ]]; then
    echo "ERROR: butterscotch binary not found at $BSCOTCH_DIR/$BINARY"
    echo "Contents of build directory:"
    ls -la build/
    exit 1
fi

echo "==> Preparing bscotch-build..."
rm -rf "$BSCOTCH_BUILD_DIR"
mkdir -p "$BSCOTCH_BUILD_DIR/build"
cp -a "$SCRIPT_DIR/bscotch"/. "$BSCOTCH_BUILD_DIR"/

echo "==> Copying binary and gamecontrollerdb.txt..."
cp -a "$BINARY" "$BSCOTCH_BUILD_DIR/build/butterscotch"
if [[ -f "build/gamecontrollerdb.txt" ]]; then
    cp -a "build/gamecontrollerdb.txt" "$BSCOTCH_BUILD_DIR/build/gamecontrollerdb.txt"
elif [[ -f "vendor/gamecontrollerdb.txt" ]]; then
    cp -a "vendor/gamecontrollerdb.txt" "$BSCOTCH_BUILD_DIR/build/gamecontrollerdb.txt"
else
    echo "WARNING: gamecontrollerdb.txt not found"
fi

echo "==> Done!"
