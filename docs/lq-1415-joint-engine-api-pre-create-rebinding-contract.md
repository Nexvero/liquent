# LQ-1415 Joint engine API pre-create rebinding contract

- Rebinding before marker creation must have zero marker side effects.
- The held original registry and new visible registry both remain empty.
- Missing, symlinked, and replaced parent paths share that result.
- Rejection occurs after encoding but before exclusive file open.
- No cleanup is needed because creation has not begun.
- A later caller must resolve and validate the boundary afresh.
- The failed call does not authorize retry or alternate-path writing.
