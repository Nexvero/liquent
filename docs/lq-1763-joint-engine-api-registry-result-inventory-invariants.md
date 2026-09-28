# LQ-1763 Joint engine API registry result inventory invariants

- Registry audit results validate their observation inventory.
- Their acceptance projection must exactly match observations.
- Projection order is therefore canonical by construction.
- Duplicate acceptance facts cannot enter the result.
- Duplicate marker generations cannot enter the result.
- Mismatched projections fail closed without detail.
- Read-only audit behavior remains unchanged.
