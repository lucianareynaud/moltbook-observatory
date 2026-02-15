#!/bin/sh
# Create Python virtual environment if it doesn't exist

set -e

VENV=".venv"
PYTHON="python3"

if [ -d "$VENV" ]; then
    echo "[venv] Virtual environment already exists at $VENV"
    exit 0
fi

echo "[venv] Creating virtual environment at $VENV..."
$PYTHON -m venv "$VENV"

echo "[venv] Virtual environment created successfully"
echo "[venv] Activate with: source $VENV/bin/activate"
