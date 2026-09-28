# LQ-1465 Joint engine API duplicate precheck evidence

- Tests replace the registry before the inner duplicate lookup.
- The replacement has the same layout and no marker entries.
- Bound one-shot acceptance rejects it without creating a marker.
- Operation-bound acceptance exhibits the same fail-closed result.
- Existing genuine-duplicate rejection remains covered elsewhere.
- Source state is not mutated by the failed precheck.
- Evidence remains local and deterministic.
