# LQ-1550 Joint engine API marker invariant audit

- LQ-1547 through LQ-1549 close marker link and size semantics.
- Canonical value and filesystem size are mutually bound.
- Forged bounded-but-incorrect state cannot become evidence.
- Capture-time checks remain independently mandatory.
- Failure remains fail-closed and detail-free.
- No schema, CLI, or mutation behavior was added.
- Decision integration remains the next boundary.
