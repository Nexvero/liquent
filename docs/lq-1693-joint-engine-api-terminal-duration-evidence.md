# LQ-1693 Joint engine API terminal duration evidence

- Tests provide deterministic three-point monotonic clocks.
- Completion at 29 seconds may still continue.
- Terminal convergence beyond 30 seconds fails.
- Stable terminal timing succeeds.
- Earlier backward and overlong checks remain active.
- Final root validation still follows the gate.
- External runtime evidence remains separate.
