# LQ-1659 Joint engine API source identity reuse contract

- Final source read uses operation-resolved identity.
- Caller cannot substitute another source generation.
- Initial and final reads receive the same identity fact.
- Path equality alone never establishes continuity.
- Source observation validates every child generation.
- Audit-only operation behavior remains unchanged.
- Identity mismatch fails detail-free.
