# LQ-1298 Joint engine API budget exhaustion audit

- Exhausted-budget behavior is deterministic and fail closed.
- No unnecessary descriptor or source content exists after exhaustion.
- The check precedes every possible child-reader side effect.
- Canonical nonempty source requirements prevent ambiguous completion.
- The behavior is shared by all source-layout generations.
- Focused exhaustion and regression tests pass under strict warnings.
- This hardening does not claim external Docker staging evidence.
