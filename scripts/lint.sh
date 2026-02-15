#!/bin/sh
# Run code linters (ruff)

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[lint] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

# Check if ruff is installed
if [ ! -f "$BIN/ruff" ]; then
    echo "[lint] Installing ruff..."
    "$BIN/pip" install --quiet ruff
fi

echo "[lint] Running ruff check..."
"$BIN/ruff" check collector/ reports/

echo "[lint] ✓ Lint checks passed"
