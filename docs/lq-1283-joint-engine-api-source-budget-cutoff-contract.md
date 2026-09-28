# LQ-1283 Joint engine API source budget cutoff contract

- Aggregate-budget rejection occurs at the first overflowing child value.
- Source names after that child must not be opened or read.
- Rejection exposes neither the overflowing value nor prior partial values.
- Canonical ordering makes the cutoff deterministic for a fixed layout.
- Per-child validation still completes before its bytes enter the total.
- Directory and source descriptors remain locally owned and closed.
- The cutoff is a defensive resource boundary, not an authorization rule.
