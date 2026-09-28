# LQ-1694 Joint engine API terminal duration audit

- LQ-1691 through LQ-1693 bind duration through convergence.
- Completion clock no longer ends elapsed accounting early.
- Terminal source observation lies inside the time budget.
- Freshness remains bound to completion UTC.
- Failure cannot erase durable acceptance evidence.
- No retry or alternate duration is admitted.
- Ordered terminal finalization remains next.
