from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CollectionHealth:
    """
    Metrics describing collection behavior and reliability for a given time window.

    Invariants:
      - total_requests >= successful_requests
      - latency_p50_ms <= latency_p95_ms <= latency_p99_ms
    """
    total_requests: int
    successful_requests: int  # status_code 2xx, no error
    failed_requests: int
    retried_requests: int  # attempt > 1
    error_distribution: Dict[str, int]  # error type -> count
    latency_p50_ms: Optional[float]
    latency_p95_ms: Optional[float]
    latency_p99_ms: Optional[float]
    endpoints_seen: List[str]


@dataclass
class PayloadStats:
    """
    Schema-defensive statistics about collected payloads.

    Does not assume any particular schema; focuses on structural properties
    that are available regardless of the platform's API structure.
    """
    total_events: int
    events_by_endpoint: Dict[str, int]  # endpoint_name -> count
    events_over_time: List[Tuple[str, int]]  # (ISO date, count) sorted chronologically
    payload_size_bytes_p50: Optional[float]
    payload_size_bytes_p95: Optional[float]
    unique_urls_collected: int


@dataclass
class WeeklyFeatures:
    """
    Complete feature set extracted from raw data for a given ISO week.

    All fields are deterministic functions of raw_events and request_log
    within the specified time range.
    """
    week_id: str  # e.g., "2026-W07"
    week_start_utc: str  # ISO timestamp
    week_end_utc: str  # ISO timestamp
    collection_health: CollectionHealth
    payload_stats: PayloadStats
    extracted_at_utc: str  # ISO timestamp of extraction


def _parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string to datetime object."""
    return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))


def _compute_percentile(sorted_values: List[float], percentile: float) -> Optional[float]:
    """
    Compute percentile from sorted list of values.

    Returns None if list is empty.
    """
    if not sorted_values:
        return None
    n = len(sorted_values)
    k = (n - 1) * percentile
    f = int(k)
    c = k - f
    if f + 1 < n:
        return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c
    return sorted_values[f]


def extract(
    sqlite_path: str,
    week_start_utc: str,
    week_end_utc: str,
) -> WeeklyFeatures:
    """
    Extract features for a given ISO week from SQLite database.

    Args:
        sqlite_path: Path to observatory.sqlite
        week_start_utc: ISO timestamp for week start (inclusive)
        week_end_utc: ISO timestamp for week end (inclusive)

    Returns:
        WeeklyFeatures dataclass with all extracted metrics

    Failure modes:
        - Raises sqlite3.Error if database is inaccessible or corrupted
        - Treats malformed JSON payloads as observability signals (logs, continues)
        - Returns zero counts if no data exists for the specified range
    """
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    try:
        # Extract collection health from request_log
        request_rows = conn.execute(
            """
            SELECT endpoint_name, status_code, elapsed_ms, attempt, error
            FROM request_log
            WHERE ts_utc >= ? AND ts_utc <= ?
            ORDER BY ts_utc ASC
            """,
            (week_start_utc, week_end_utc),
        ).fetchall()

        total_requests = len(request_rows)
        successful_requests = 0
        failed_requests = 0
        retried_requests = 0
        error_distribution: Dict[str, int] = {}
        latencies: List[float] = []
        endpoints_seen_set = set()

        for row in request_rows:
            endpoints_seen_set.add(row["endpoint_name"])

            if row["attempt"] > 1:
                retried_requests += 1

            if row["error"] is None and row["status_code"] and 200 <= row["status_code"] < 300:
                successful_requests += 1
            else:
                failed_requests += 1

            if row["error"]:
                error_type = row["error"].split(":")[0]  # e.g., "network" from "network:TimeoutException"
                error_distribution[error_type] = error_distribution.get(error_type, 0) + 1

            if row["elapsed_ms"] is not None:
                latencies.append(float(row["elapsed_ms"]))

        latencies.sort()

        health = CollectionHealth(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            retried_requests=retried_requests,
            error_distribution=error_distribution,
            latency_p50_ms=_compute_percentile(latencies, 0.50),
            latency_p95_ms=_compute_percentile(latencies, 0.95),
            latency_p99_ms=_compute_percentile(latencies, 0.99),
            endpoints_seen=sorted(endpoints_seen_set),
        )

        # Extract payload stats from raw_events
        event_rows = conn.execute(
            """
            SELECT endpoint_name, url, ts_utc, payload_json
            FROM raw_events
            WHERE ts_utc >= ? AND ts_utc <= ?
            ORDER BY ts_utc ASC
            """,
            (week_start_utc, week_end_utc),
        ).fetchall()

        total_events = len(event_rows)
        events_by_endpoint: Dict[str, int] = {}
        events_by_date: Dict[str, int] = {}  # ISO date -> count
        payload_sizes: List[float] = []
        unique_urls = set()

        for row in event_rows:
            # Count by endpoint
            endpoint = row["endpoint_name"]
            events_by_endpoint[endpoint] = events_by_endpoint.get(endpoint, 0) + 1

            # Count by date
            try:
                ts = _parse_iso_timestamp(row["ts_utc"])
                date_key = ts.date().isoformat()
                events_by_date[date_key] = events_by_date.get(date_key, 0) + 1
            except Exception:
                pass  # Malformed timestamp; skip time-series bucketing for this row

            # Track URL uniqueness
            unique_urls.add(row["url"])

            # Measure payload size
            payload_json = row["payload_json"]
            if payload_json:
                payload_sizes.append(float(len(payload_json.encode("utf-8"))))

        payload_sizes.sort()
        events_over_time = sorted(events_by_date.items(), key=lambda x: x[0])

        stats = PayloadStats(
            total_events=total_events,
            events_by_endpoint=events_by_endpoint,
            events_over_time=events_over_time,
            payload_size_bytes_p50=_compute_percentile(payload_sizes, 0.50),
            payload_size_bytes_p95=_compute_percentile(payload_sizes, 0.95),
            unique_urls_collected=len(unique_urls),
        )

        # Derive week_id from week_start
        try:
            week_start_dt = _parse_iso_timestamp(week_start_utc)
            week_id = f"{week_start_dt.year}-W{week_start_dt.isocalendar()[1]:02d}"
        except Exception:
            week_id = "unknown"

        return WeeklyFeatures(
            week_id=week_id,
            week_start_utc=week_start_utc,
            week_end_utc=week_end_utc,
            collection_health=health,
            payload_stats=stats,
            extracted_at_utc=datetime.utcnow().isoformat() + "Z",
        )

    finally:
        conn.close()
