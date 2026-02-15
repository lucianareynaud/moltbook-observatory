from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from reports.features import WeeklyFeatures


@dataclass
class AnomalyFlag:
    """
    A single anomaly detection signal.

    Fields:
        severity: "info" | "warning" | "critical"
        category: Human-readable grouping (e.g., "collection_health", "volume")
        message: Plain-English description of the anomaly
        context: Optional structured data for debugging
    """

    severity: str
    category: str
    message: str
    context: Optional[Dict[str, float]] = None


@dataclass
class WeeklyScores:
    """
    Risk signals and anomaly flags derived from WeeklyFeatures.

    Epistemic constraint: scores are triage signals, not verdicts.
    Thresholds documented in docs/methodology.md.
    """

    week_id: str
    availability_by_endpoint: Dict[str, float]  # endpoint_name -> ratio [0.0, 1.0]
    overall_availability: float  # weighted or simple average
    volume_change_pct: Optional[float]  # vs prior week, if comparable data exists
    anomalies: List[AnomalyFlag] = field(default_factory=list)
    scored_at_utc: str = ""


# Thresholds (documented in methodology.md, repeated here for auditability)
AVAILABILITY_WARNING_THRESHOLD = 0.90  # warn if < 90%
AVAILABILITY_CRITICAL_THRESHOLD = 0.50  # critical if < 50%
VOLUME_CHANGE_WARNING_THRESHOLD = 2.0  # warn if >2x or <0.5x prior week
ERROR_RATE_WARNING_THRESHOLD = 0.10  # warn if >10% of requests have errors


def score(
    features: WeeklyFeatures, prior_week_features: Optional[WeeklyFeatures] = None
) -> WeeklyScores:
    """
    Derive risk signals and anomaly flags from extracted features.

    Args:
        features: Current week's features
        prior_week_features: Optional features from previous week for trend comparison

    Returns:
        WeeklyScores with availability metrics and anomaly flags

    Failure modes:
        - If no requests were made, availability is undefined (represented as 0.0 with info flag)
        - If no prior week data, volume_change_pct is None
    """
    from datetime import datetime

    anomalies: List[AnomalyFlag] = []
    health = features.collection_health
    stats = features.payload_stats

    # Compute per-endpoint availability
    availability_by_endpoint: Dict[str, float] = {}

    if health.total_requests == 0:
        overall_availability = 0.0
        anomalies.append(
            AnomalyFlag(
                severity="info",
                category="collection_health",
                message="No requests made during this week",
            )
        )
    else:
        overall_availability = health.successful_requests / health.total_requests

        # Per-endpoint availability (approximation: cannot directly attribute success to endpoint from current schema)
        # For MVP, use overall availability as proxy for each endpoint
        for endpoint in health.endpoints_seen:
            availability_by_endpoint[endpoint] = overall_availability

        # Flag low availability
        if overall_availability < AVAILABILITY_CRITICAL_THRESHOLD:
            anomalies.append(
                AnomalyFlag(
                    severity="critical",
                    category="collection_health",
                    message=f"Critical availability drop: {overall_availability:.1%}",
                    context={
                        "availability": overall_availability,
                        "threshold": AVAILABILITY_CRITICAL_THRESHOLD,
                    },
                )
            )
        elif overall_availability < AVAILABILITY_WARNING_THRESHOLD:
            anomalies.append(
                AnomalyFlag(
                    severity="warning",
                    category="collection_health",
                    message=f"Low availability: {overall_availability:.1%}",
                    context={
                        "availability": overall_availability,
                        "threshold": AVAILABILITY_WARNING_THRESHOLD,
                    },
                )
            )

        # Flag high error rates
        error_rate = health.failed_requests / health.total_requests
        if error_rate > ERROR_RATE_WARNING_THRESHOLD:
            anomalies.append(
                AnomalyFlag(
                    severity="warning",
                    category="collection_health",
                    message=f"Elevated error rate: {error_rate:.1%}",
                    context={
                        "error_rate": error_rate,
                        "threshold": ERROR_RATE_WARNING_THRESHOLD,
                    },
                )
            )

    # Compute volume change vs prior week
    volume_change_pct: Optional[float] = None
    if prior_week_features is not None:
        prior_total = prior_week_features.payload_stats.total_events
        current_total = stats.total_events

        if prior_total > 0:
            volume_change_pct = ((current_total - prior_total) / prior_total) * 100

            # Flag significant volume changes
            abs_change_ratio = current_total / prior_total if prior_total > 0 else 0
            if (
                abs_change_ratio > VOLUME_CHANGE_WARNING_THRESHOLD
                or abs_change_ratio < (1.0 / VOLUME_CHANGE_WARNING_THRESHOLD)
            ):
                anomalies.append(
                    AnomalyFlag(
                        severity="warning",
                        category="volume",
                        message=f"Significant volume change: {volume_change_pct:+.1f}% vs prior week",
                        context={
                            "volume_change_pct": volume_change_pct,
                            "current": current_total,
                            "prior": prior_total,
                        },
                    )
                )

    # Flag if no events were collected despite requests
    if stats.total_events == 0 and health.successful_requests > 0:
        anomalies.append(
            AnomalyFlag(
                severity="warning",
                category="volume",
                message="No events stored despite successful requests",
            )
        )

    return WeeklyScores(
        week_id=features.week_id,
        availability_by_endpoint=availability_by_endpoint,
        overall_availability=overall_availability,
        volume_change_pct=volume_change_pct,
        anomalies=anomalies,
        scored_at_utc=datetime.utcnow().isoformat() + "Z",
    )
