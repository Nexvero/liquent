# LQ-1705 Joint engine API audit post-success replacement evidence

- Tests let accepted-source inner audit succeed.
- They then replace the marker with identical bytes and mode.
- Root identity remains unchanged.
- Marker observation identity changes.
- Outer success check rejects the audit.
- Stable registry and accepted-source audits succeed.
- Evidence is local and deterministic.
