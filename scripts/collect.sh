#!/bin/sh
# Run collector once to fetch data

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[collect] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

# Check required environment variables
if [ -z "$MOLTBOOK_BASE_URL" ]; then
    echo "[collect] ERROR: MOLTBOOK_BASE_URL environment variable not set"
    echo "[collect] Set it with: export MOLTBOOK_BASE_URL='https://www.moltbook.com'"
    exit 1
fi

if [ -z "$MOLTBOOK_ENDPOINTS_JSON" ]; then
    echo "[collect] ERROR: MOLTBOOK_ENDPOINTS_JSON environment variable not set"
    echo "[collect] Example: export MOLTBOOK_ENDPOINTS_JSON='[{\"name\":\"posts_hot\",\"path_template\":\"/api/v1/posts?sort=hot&limit=5\",\"params\":{}}]'"
    exit 1
fi

echo "[collect] Running collector..."
"$BIN/python" -m collector.main
