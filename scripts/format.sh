#!/bin/sh
# Format code with ruff

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[format] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

# Check if ruff is installed
if [ ! -f "$BIN/ruff" ]; then
    echo "[format] Installing ruff..."
    "$BIN/pip" install --quiet ruff
fi

# Check if --check flag is passed
if [ "$1" = "--check" ]; then
    echo "[format] Checking code formatting..."
    "$BIN/ruff" format --check collector/ reports/
    echo "[format] ✓ Format check passed"
else
    echo "[format] Formatting code..."
    "$BIN/ruff" format collector/ reports/
    echo "[format] ✓ Code formatted"
fi
