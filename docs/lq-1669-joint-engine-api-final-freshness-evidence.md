# LQ-1669 Joint engine API final freshness evidence

- Tests keep inner verification time valid.
- They advance only the outer final wall time.
- Retained source then exceeds configured freshness.
- Outer operation rejects completed success.
- Stable final time remains successful.
- Marker may remain for later read-only audit.
- No rollback behavior is claimed.
