# LQ-1571 Joint engine API operation state continuity contract

- Operation root and source state must remain unchanged.
- Audit requires unchanged acceptance state as well.
- Same-inode metadata changes remain observable through state.
- Final resolution must match the initial closed topology.
- Identity continuity alone is insufficient.
- Mismatch fails after success or failure.
- No retry or fallback topology is used.
