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
Create a virtual environment, install requirements, then define the base URL and endpoint specs.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Create your endpoint configuration (example only; do not assume these paths exist in production):

```bash
export MOLTBOOK_BASE_URL="https://www.moltbook.com"
export MOLTBOOK_ENDPOINTS_JSON='[
  {"name":"global_hot","path_template":"/api/v1/posts?sort=hot&limit={limit}","params":{"limit":25}}
]'
python -m collector.main
```

If an endpoint requires authentication, set `MOLTBOOK_AUTH_BEARER`:

```bash
export MOLTBOOK_AUTH_BEARER="YOUR_TOKEN_HERE"
python -m collector.main
```

Validate that data were stored:

```bash
sqlite3 data/observatory.sqlite "SELECT COUNT(*) FROM raw_events;"
```

## Safety
The collector is designed to be non-invasive: it performs no side effects, avoids DMs, respects rate limits, and logs failures rather than retrying aggressively. If you change endpoints or add credentials, treat the system as a potential security boundary and apply least-privilege discipline.

## License
MIT
