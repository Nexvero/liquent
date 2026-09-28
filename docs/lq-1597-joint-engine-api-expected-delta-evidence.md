# LQ-1597 Joint engine API expected delta evidence

- Tests observe source identity on expected-value derivation.
- Canonical marker for a different run is rejected.
- Same-run marker with wrong envelope hash is rejected.
- Exact source-derived marker succeeds.
- Existing single-addition tests remain green.
- No failure exposes run or digest details.
- Evidence is local and deterministic.
