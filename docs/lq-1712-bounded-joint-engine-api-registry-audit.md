# LQ-1712 Bounded joint engine API registry audit

- Registry audit captures outer monotonic start and finish.
- Both root resolutions lie inside the interval.
- Both value and observation inventory reads lie inside it.
- Exactly 30 seconds remains accepted.
- Registry mode needs no wall-clock freshness.
- No timeout value or CLI option is added.
- Overrun fails unavailable.
