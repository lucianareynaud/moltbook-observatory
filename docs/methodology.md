# Methodology Notes

## Epistemic posture
Public interaction traces are not ground truth. A conservative integrity observatory must not commit the category error of treating observable regularities as proof of authorship class. We define **integrity risk** as the likelihood that observed patterns are produced by coordination, automation misuse, or manipulation; scores are therefore triage signals intended for prioritization, not adjudication.

## Feature families and confounders
Temporal burstiness may reflect time zones, scheduled content, or high-activity accounts; lexical redundancy may reflect narrow topical focus; synchronization may emerge from genuine external events. For each feature, cohort-normalized residuals are preferable to naive global thresholds. Reports should separate descriptive statistics (what happened) from anomaly detection (what deviated) and interpretive hypotheses (possible explanations, explicitly labeled as hypotheses).

## Evaluation discipline
If supervised modeling is introduced, it must include clear label provenance, a holdout protocol, calibration analysis, and error analysis that treats false positives as first-class failure modes.

---

## MVP Features (v0.1.0)

### Collection Health Features
Metrics derived from `request_log` table:
- **Total requests**: Count of all HTTP requests attempted
- **Successful requests**: Requests with 2xx status and no error field
- **Failed requests**: Requests with errors or non-2xx status
- **Retried requests**: Requests with attempt > 1
- **Error distribution**: Histogram of error types (network, auth, retryable_status, json_parse)
- **Latency percentiles**: p50, p95, p99 of elapsed_ms for all requests
- **Endpoints seen**: Unique endpoint_name values

### Payload Statistics Features
Metrics derived from `raw_events` table:
- **Total events**: Count of stored payloads
- **Events by endpoint**: Histogram of endpoint_name
- **Events over time**: Daily time series of event counts
- **Payload size percentiles**: p50, p95 of payload_json byte size
- **Unique URLs collected**: Distinct url values

### Anomaly Detection (v0.1.0)
Conservative thresholds applied to derived features:
- **Availability warning**: overall_availability < 0.90 (90%)
- **Availability critical**: overall_availability < 0.50 (50%)
- **Error rate warning**: (failed_requests / total_requests) > 0.10 (10%)
- **Volume change warning**: week-over-week change > 2x or < 0.5x (requires prior week data)

All thresholds are provisional and subject to revision based on empirical observation.

### Known Limitations (v0.1.0)
- **No schema-specific features**: Payload contents are not parsed; only structural properties (size, count) are extracted
- **No author-level features**: No identity resolution or behavioral profiling
- **No coordination detection**: No temporal correlation or synchronization analysis
- **Endpoint availability is approximated**: Current schema does not directly link request_log entries to raw_events, so per-endpoint success rates use overall availability as proxy
- **No trend baselines**: Week-over-week comparison is naive delta; no seasonal adjustment or cohort normalization
