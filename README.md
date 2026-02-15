# Moltbook Integrity Observatory

## Abstract
Agent-centric social platforms introduce a practical ambiguity: identical surface interaction patterns (posting, replying, voting, reputation accrual) may be produced by autonomous agents, humans impersonating agents, coordinated groups, or mixed-mode accounts. This repository implements a conservative, *public-only* observability layer that (i) measures macro dynamics (topics, growth, engagement), (ii) detects coordination anomalies (brigading, astroturfing, spam bursts), and (iii) surfaces integrity risk signals through an auditable scoring methodology. It explicitly does **not** claim ground-truth authorship attribution; instead, it provides triage-oriented signals with documented uncertainty.

## Motivation
In early-stage agent networks, narrative proliferates faster than measurement, while security and integrity risks scale nonlinearly with automation. The highest-leverage contribution is therefore instrumentation: making the environment legible, reproducible, and auditable, without privileged access.

## Scope and Non-Goals
This project includes a hardened collector for public endpoints, immutable raw-payload storage, request-level logging, and a methodology-first analysis layer (to be extended with features, scoring, and reporting). It does **not** ingest DMs, does not use private endpoints, does not perform posting or engagement actions, and does not attempt de-anonymization or fingerprinting. Scores are **risk indicators**, not verdicts.

## Architecture (MVP)
The system is split into two planes. The **collection plane** fetches public endpoints with strict rate limiting and robust retry semantics, then persists raw JSON and request logs to a local SQLite database. The **analysis plane** derives features from immutable raw data and produces weekly reports and dashboard-ready tables; in the MVP, the analysis layer can be added incrementally without rewriting the collector.

## Reproducibility
All analytical outputs are deterministically derivable from stored raw events and the code in this repository, subject to the volatility of public endpoints. Feature definitions and score weights should be versioned once introduced.

## Quickstart

### Setup (one-time)

```bash
# Create virtual environment and install dependencies
make setup

# Or manually:
make venv
make install
```

### Configure endpoints

Set environment variables for the platform API you're observing:

```bash
export MOLTBOOK_BASE_URL="https://www.moltbook.com"
export MOLTBOOK_ENDPOINTS_JSON='[
  {"name":"posts_hot","path_template":"/api/v1/posts?sort=hot&limit={limit}","params":{"limit":25}}
]'
```

If authentication is required:

```bash
export MOLTBOOK_AUTH_BEARER="YOUR_TOKEN_HERE"
```

### Collect data

```bash
# Run collector once
make collect

# Validate data were stored
sqlite3 data/observatory.sqlite "SELECT COUNT(*) FROM raw_events;"
```

### Analysis & reporting

```bash
# Extract features only (for inspection)
make features

# Generate report for previous complete week
make report

# Generate report for current week
make report-current

# Build static site index from all reports
make build-site

# View generated artifacts
ls -lh output/$(date -u +"%Y-W%V")/
open output/site/index.html  # or xdg-open on Linux
```

### Development workflow

```bash
# Format code
make format

# Run linters
make lint

# Check formatting (CI-friendly)
make check

# Clean generated files
make clean
```

### All available commands

```bash
make help
```

## Safety
The collector is designed to be non-invasive: it performs no side effects, avoids DMs, respects rate limits, and logs failures rather than retrying aggressively. If you change endpoints or add credentials, treat the system as a potential security boundary and apply least-privilege discipline.

## License
MIT

# Moltbook Observatory (WIP)

## Status: Architecture Complete, Implementation In Progress

✅ Completed:
- System architecture
- Data collection pipeline
- Methodology documentation
- Makefile automation

🚧 In Progress:
- Feature extraction pipeline
- Weekly reporting system

This is a work-in-progress portfolio piece demonstrating 
MLOps/observability system design.
