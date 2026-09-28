# LQ-1539 Joint engine API closed source decision contract

- Accept and audit consume only semantically closed observations.
- Observation construction precedes cryptographic decision use.
- Invalid root or child state cannot become verification evidence.
- Caller-supplied roles or allow flags remain irrelevant.
- Source identity and convergence remain independently required.
- Failure creates no alternate evidence path.
- Technical details remain internal.
