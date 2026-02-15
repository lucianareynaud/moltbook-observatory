#!/bin/sh
# Generate weekly report

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[report] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

# Check if --current flag is passed
if [ "$1" = "--current" ]; then
    # Get current ISO week
    WEEK=$(date -u +"%Y-W%V" 2>/dev/null || date -u +"%G-W%V")
    echo "[report] Generating report for current week: $WEEK"
    "$BIN/python" -m reports.run_weekly --week "$WEEK"
else
    echo "[report] Generating report for previous complete week..."
    "$BIN/python" -m reports.run_weekly
fi
