from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, Template

from reports.features import WeeklyFeatures
from reports.scoring import WeeklyScores


def _get_template_env() -> Environment:
    """Create Jinja2 environment with templates directory."""
    templates_dir = Path(__file__).parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _format_bytes(num_bytes: float) -> str:
    """Format bytes as human-readable string (KB, MB)."""
    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f} MB"


def _format_ms(ms: float) -> str:
    """Format milliseconds as human-readable string."""
    if ms < 1000:
        return f"{ms:.0f} ms"
    else:
        return f"{ms / 1000:.2f} s"


def _prepare_context(features: WeeklyFeatures, scores: WeeklyScores) -> Dict[str, Any]:
    """
    Prepare template context from features and scores.

    Returns dictionary suitable for passing to Jinja2 templates.
    """
    health = features.collection_health
    stats = features.payload_stats

    # Helper: format anomalies for display
    anomalies_by_severity = {"critical": [], "warning": [], "info": []}
    for anomaly in scores.anomalies:
        anomalies_by_severity[anomaly.severity].append(anomaly)

    # Helper: prepare chart data
    events_over_time_labels = [date for date, _ in stats.events_over_time]
    events_over_time_values = [count for _, count in stats.events_over_time]

    return {
        "week_id": features.week_id,
        "week_start": features.week_start_utc,
        "week_end": features.week_end_utc,
        "extracted_at": features.extracted_at_utc,
        "scored_at": scores.scored_at_utc,

        # Collection health
        "total_requests": health.total_requests,
        "successful_requests": health.successful_requests,
        "failed_requests": health.failed_requests,
        "retried_requests": health.retried_requests,
        "error_distribution": health.error_distribution,
        "latency_p50_ms": health.latency_p50_ms,
        "latency_p95_ms": health.latency_p95_ms,
        "latency_p99_ms": health.latency_p99_ms,
        "endpoints_seen": health.endpoints_seen,

        # Payload stats
        "total_events": stats.total_events,
        "events_by_endpoint": stats.events_by_endpoint,
        "events_over_time": stats.events_over_time,
        "events_over_time_labels": events_over_time_labels,
        "events_over_time_values": events_over_time_values,
        "payload_size_p50": stats.payload_size_bytes_p50,
        "payload_size_p95": stats.payload_size_bytes_p95,
        "unique_urls": stats.unique_urls_collected,

        # Scores
        "availability_by_endpoint": scores.availability_by_endpoint,
        "overall_availability": scores.overall_availability,
        "volume_change_pct": scores.volume_change_pct,
        "anomalies": scores.anomalies,
        "anomalies_by_severity": anomalies_by_severity,

        # Helper functions
        "format_bytes": _format_bytes,
        "format_ms": _format_ms,
        "format_pct": lambda x: f"{x:.1%}",
    }


def render_report(features: WeeklyFeatures, scores: WeeklyScores) -> str:
    """
    Render Markdown report from features and scores.

    Args:
        features: Extracted features for the week
        scores: Derived scores and anomaly flags

    Returns:
        Markdown string ready to write to file

    Failure modes:
        - Raises jinja2.TemplateError if template is malformed
        - Raises if templates/weekly_report.md.j2 is missing
    """
    env = _get_template_env()
    template = env.get_template("weekly_report.md.j2")
    context = _prepare_context(features, scores)
    return template.render(**context)


def render_dashboard(features: WeeklyFeatures, scores: WeeklyScores) -> str:
    """
    Render single-file HTML dashboard from features and scores.

    Args:
        features: Extracted features for the week
        scores: Derived scores and anomaly flags

    Returns:
        Complete HTML string (self-contained, Chart.js via CDN)

    Failure modes:
        - Raises jinja2.TemplateError if template is malformed
        - Raises if templates/dashboard.html.j2 is missing
    """
    env = _get_template_env()
    template = env.get_template("dashboard.html.j2")
    context = _prepare_context(features, scores)
    return template.render(**context)
