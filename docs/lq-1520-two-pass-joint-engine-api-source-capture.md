# LQ-1520 Two-pass joint engine API source capture

- The established budgeted child loader performs the first pass.
- A second descriptor pass captures content and complete state.
- All fourteen values must equal their first-pass counterparts.
- Existing aggregate and per-file budgets remain authoritative.
- Final visible-root validation follows both passes.
- Snapshot construction occurs only after convergence.
- Existing snapshot-only loader remains compatible.
