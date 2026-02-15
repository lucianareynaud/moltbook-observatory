#!/usr/bin/env python3
"""
Weekly reporting CLI for Moltbook Observatory.

Usage:
    python -m reports.run_weekly                  # previous complete ISO week
    python -m reports.run_weekly --week 2026-W07  # explicit week
    python -m reports.run_weekly --help

Environment variables:
    MOLTBOOK_SQLITE_PATH: Path to observatory.sqlite (default: data/observatory.sqlite)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reports import features, scoring, render


def parse_iso_week(week_str: str) -> tuple[str, str]:
    """
    Parse ISO week string (e.g., "2026-W07") to (week_start_utc, week_end_utc) ISO timestamps.

    ISO week starts on Monday 00:00:00 UTC and ends on Sunday 23:59:59 UTC.

    Args:
        week_str: ISO week string in format "YYYY-Wnn"

    Returns:
        Tuple of (week_start_utc, week_end_utc) as ISO strings

    Raises:
        ValueError: If week_str is malformed
    """
    try:
        parts = week_str.split("-W")
        if len(parts) != 2:
            raise ValueError("Expected format: YYYY-Wnn")

        year = int(parts[0])
        week = int(parts[1])

        if week < 1 or week > 53:
            raise ValueError("Week number must be between 1 and 53")

        # ISO week 1 is the first week with at least 4 days in January
        # Find Jan 4th of the year, then find the Monday of that week
        jan_4 = datetime(year, 1, 4, tzinfo=timezone.utc)
        week_1_monday = jan_4 - timedelta(days=jan_4.weekday())

        # Calculate target week's Monday
        target_monday = week_1_monday + timedelta(weeks=week - 1)
        target_sunday = target_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return (
            target_monday.isoformat().replace("+00:00", "Z"),
            target_sunday.isoformat().replace("+00:00", "Z"),
        )

    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid ISO week format '{week_str}': {e}") from e


def get_previous_complete_week() -> str:
    """
    Get the ISO week ID for the previous complete week.

    Returns:
        ISO week string in format "YYYY-Wnn"
    """
    now = datetime.now(timezone.utc)
    # Go back to the previous Sunday, then back one more week to get a complete week
    days_since_monday = now.weekday()
    last_sunday = now - timedelta(days=days_since_monday + 1)
    # Get the ISO calendar week for that Sunday
    iso_calendar = last_sunday.isocalendar()
    return f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"


def main() -> int:
    """
    Main entry point for weekly report generation.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Generate weekly integrity reports from collected data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--week",
        type=str,
        help="ISO week to process (e.g., 2026-W07). Default: previous complete week",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for artifacts (default: output/)",
    )

    args = parser.parse_args()

    # Determine target week
    if args.week:
        week_id = args.week
    else:
        week_id = get_previous_complete_week()
        print(f"[reports] Using previous complete week: {week_id}")

    try:
        week_start_utc, week_end_utc = parse_iso_week(week_id)
    except ValueError as e:
        print(f"[reports] ERROR: {e}", file=sys.stderr)
        return 1

    # Load SQLite path from environment
    sqlite_path = os.environ.get("MOLTBOOK_SQLITE_PATH", "data/observatory.sqlite")

    if not Path(sqlite_path).exists():
        print(f"[reports] ERROR: Database not found at {sqlite_path}", file=sys.stderr)
        return 1

    print(f"[reports] Extracting features for {week_id} ({week_start_utc} to {week_end_utc})...")

    try:
        # Extract features
        weekly_features = features.extract(sqlite_path, week_start_utc, week_end_utc)

        # Compute scores (no prior week comparison in MVP)
        weekly_scores = scoring.score(weekly_features, prior_week_features=None)

        # Render artifacts
        report_md = render.render_report(weekly_features, weekly_scores)
        dashboard_html = render.render_dashboard(weekly_features, weekly_scores)

        # Write to output directory
        output_path = Path(args.output_dir) / week_id
        output_path.mkdir(parents=True, exist_ok=True)

        report_path = output_path / "report.md"
        dashboard_path = output_path / "dashboard.html"

        report_path.write_text(report_md, encoding="utf-8")
        dashboard_path.write_text(dashboard_html, encoding="utf-8")

        print(f"[reports] ✓ Generated artifacts:")
        print(f"[reports]   - {report_path}")
        print(f"[reports]   - {dashboard_path}")
        print(f"[reports]")
        print(f"[reports] Summary:")
        print(f"[reports]   Total events: {weekly_features.payload_stats.total_events}")
        print(f"[reports]   Total requests: {weekly_features.collection_health.total_requests}")
        print(f"[reports]   Availability: {weekly_scores.overall_availability:.1%}")
        print(f"[reports]   Anomalies: {len(weekly_scores.anomalies)}")

        if weekly_scores.anomalies:
            print(f"[reports]")
            print(f"[reports] Anomalies detected:")
            for anomaly in weekly_scores.anomalies:
                print(f"[reports]   [{anomaly.severity.upper()}] {anomaly.message}")

        return 0

    except Exception as e:
        print(f"[reports] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
