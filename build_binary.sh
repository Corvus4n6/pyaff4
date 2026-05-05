#!/usr/bin/env bash
# Build a standalone aff4 binary for Linux or macOS using PyInstaller.
#
# Usage:
#   ./build_binary.sh
#
# Prerequisites:
#   pip install pyinstaller
#   pip install -r requirements.txt
#
# Output: dist/aff4

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Cleaning previous build artifacts..."
rm -rf build dist

echo "==> Building standalone binary..."
pyinstaller aff4.spec

echo ""
echo "==> Build complete. Binary is at: dist/aff4"
echo "    Size: $(du -sh dist/aff4 | cut -f1)"
echo ""
echo "    Test with: dist/aff4 --help"
