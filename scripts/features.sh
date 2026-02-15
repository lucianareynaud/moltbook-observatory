#!/bin/sh
# Extract features from collected data for a given week

set -e

VENV=".venv"
BIN="$VENV/bin"

if [ ! -d "$VENV" ]; then
    echo "[features] ERROR: Virtual environment not found. Run 'make setup' first."
    exit 1
fi

# Default to current week if not specified
if [ -n "$1" ]; then
    WEEK="$1"
else
    WEEK=$(date -u +"%Y-W%V" 2>/dev/null || date -u +"%G-W%V")
fi

echo "[features] Extracting features for week: $WEEK"

# Run feature extraction (outputs JSON to stdout for inspection)
"$BIN/python" -c "
import sys
sys.path.insert(0, '.')
from reports import features
from reports.run_weekly import parse_iso_week
import os
import json

week_start, week_end = parse_iso_week('$WEEK')
sqlite_path = os.environ.get('MOLTBOOK_SQLITE_PATH', 'data/observatory.sqlite')

weekly_features = features.extract(sqlite_path, week_start, week_end)

# Output summary
print(f'Week: {weekly_features.week_id}')
print(f'Period: {weekly_features.week_start_utc} to {weekly_features.week_end_utc}')
print(f'Total events: {weekly_features.payload_stats.total_events}')
print(f'Total requests: {weekly_features.collection_health.total_requests}')
print(f'Successful requests: {weekly_features.collection_health.successful_requests}')
print(f'Endpoints: {', '.join(weekly_features.collection_health.endpoints_seen)}')
"
