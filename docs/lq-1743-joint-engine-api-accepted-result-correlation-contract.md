# LQ-1743 Joint engine API accepted result correlation contract

- Accepted marker run must equal retained source run.
- Marker envelope hash must derive from retained envelope bytes.
- Schema version remains the canonical acceptance version.
- Source and marker types must be exact.
- Caller run id or expected hash is never accepted.
- Correlation occurs during immutable construction.
- Mismatch fails detail-free.
