# LQ-1394 Joint engine API acceptance root mutation audit

- Transient private-mode restoration cannot hide root mutation.
- Timestamp changes cannot retain a valid read-only root snapshot.
- Load and inspection have symmetric failure behavior.
- Existing marker-level stability remains independently required.
- Record is not rejected merely for its intended directory mutation.
- Focused failure-window and compatibility evidence passes.
- No mutation or cleanup capability is introduced.
