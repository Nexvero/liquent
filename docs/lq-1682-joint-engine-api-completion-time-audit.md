# LQ-1682 Joint engine API completion time audit

- LQ-1679 through LQ-1681 bind time to convergence completion.
- Earlier verification time no longer ends duration accounting.
- Final freshness is evaluated at actual completion time.
- Backward wall or monotonic movement remains rejected.
- Durable marker history is never erased on failure.
- No timing policy value changed.
- Ordered completion evidence remains next.
