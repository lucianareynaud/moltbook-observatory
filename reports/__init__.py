"""
Weekly reporting pipeline for Moltbook Observatory.

Deterministically transforms raw collection data into public artifacts:
  - Markdown reports (human-readable summaries)
  - Static HTML dashboards (single-file, self-contained)

All outputs are reproducible from immutable raw_events and request_log tables.
"""

__version__ = "0.1.0"
