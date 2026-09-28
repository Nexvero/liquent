# LQ-1665 Joint engine API operation duration evidence

- Tests supply deterministic monotonic values.
- A 29-second outer interval succeeds.
- A duration above 30 seconds fails.
- Backward monotonic movement fails.
- Marker persistence never converts failure to success.
- Existing inner duration tests remain independent.
- Evidence is local and deterministic.
