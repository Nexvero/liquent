# LQ-1707 Joint engine API registry audit recheck contract

- Registry values are inspected twice on success.
- Marker observation inventory is also read twice.
- Both pairs must remain exactly equal.
- Value equality cannot hide generation replacement.
- Observation equality cannot replace canonical decoding.
- Empty and populated registries remain supported.
- Unknown entries fail closed.
