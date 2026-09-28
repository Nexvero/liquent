# LQ-1783 Joint engine API terminal registry inventory contract

- Accept finalization reobserves the complete registry inventory.
- The observation occurs after final source and marker checks.
- It must equal the closed result inventory exactly.
- Unrelated marker drift therefore fails closed.
- Ordering and complete observation state remain significant.
- The check is read-only and detail-free.
- Public accept-once behavior remains unchanged.
