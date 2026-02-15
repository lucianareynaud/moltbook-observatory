#!/bin/sh
# Install Python dependencies into virtual environment

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[install] ERROR: Virtual environment not found. Run 'make venv' first."
    exit 1
fi

echo "[install] Installing dependencies from requirements.txt..."
"$BIN/pip" install --quiet --upgrade pip
"$BIN/pip" install --quiet -r requirements.txt

echo "[install] Dependencies installed successfully"
