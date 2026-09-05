# LQ-1525 Joint engine API pre-accept convergence evidence

- Tests mutate one child after the first initial-source pass.
- The second pass observes different canonical bytes.
- One-shot acceptance rejects before marker creation.
- The acceptance registry remains empty.
- Stable source acceptance remains covered.
- Existing duplicate and identity checks remain green.
- Strict warning treatment guards regressions.
