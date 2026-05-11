#!/usr/bin/env bash
# Build a standalone aff4 binary for Linux x86_64 using PyInstaller.
#
# Usage:
#   ./build_binary.sh
#
# Prerequisites:
#   pip install pyinstaller
#   pip install -r requirements.txt
#
# Output:
#   dist/aff4                             (unversioned symlink)
#   dist/aff4-<semver>-linux-x86_64      (versioned copy)
#   dist/aff4-<semver>-linux-x86_64.sha256

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Platform guard ────────────────────────────────────────────────────────────
ARCH="$(uname -m)"
OS="$(uname -s)"
if [[ "$OS" != "Linux" || "$ARCH" != "x86_64" ]]; then
    echo "ERROR: this script targets Linux x86_64 (got $OS $ARCH)." >&2
    exit 1
fi

# ── Clean ─────────────────────────────────────────────────────────────────────
echo "==> Cleaning previous build artifacts..."
rm -rf build dist

# ── Build ─────────────────────────────────────────────────────────────────────
echo "==> Python: $(python --version)"
echo "==> PyInstaller: $(pyinstaller --version)"
echo ""
echo "==> Building standalone binary..."
pyinstaller aff4.spec

# ── Smoke test ────────────────────────────────────────────────────────────────
echo ""
echo "==> Smoke-testing binary..."
SEMVER="$(dist/aff4 --version)"
echo "    dist/aff4 --version → $SEMVER"

# ── Version-stamped copy ─────────────────────────────────────────────────────
# Replace '+' with '_' so the filename is shell/filesystem-safe.
SAFE_VER="${SEMVER//+/_}"
VERSIONED="dist/aff4-${SAFE_VER}-linux-x86_64"

cp dist/aff4 "$VERSIONED"
sha256sum "$VERSIONED" > "${VERSIONED}.sha256"
echo "    checksum: $(cat "${VERSIONED}.sha256")"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "==> Build complete."
printf "    %-42s  %s\n" "$VERSIONED" "$(du -sh "$VERSIONED" | cut -f1)"
printf "    %-42s\n"     "${VERSIONED}.sha256"
echo ""
echo "    Quick test:  $VERSIONED --help"
