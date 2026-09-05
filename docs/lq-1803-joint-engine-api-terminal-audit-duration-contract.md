# LQ-1803 Joint engine API terminal audit duration contract

- Terminal registry reads remain inside the audit budget.
- A final monotonic reading follows both terminal reads.
- Total duration remains limited to thirty seconds.
- Clock rollback between decisions fails closed.
- Slow terminal convergence cannot escape the budget.
- No wall-clock dependency is added to registry audit.
- Timing failure remains detail-free.
