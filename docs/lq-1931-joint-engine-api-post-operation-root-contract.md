# LQ-1931 Joint engine API post-operation root contract

- Success path resolves operation roots a second time.
- Second result crosses the same exact type gate.
- Accept may account only for acceptance-state change.
- Read-only audit requires complete root equality.
- Malformed second result prevents success callback.
- Final root validation still executes afterward.
- Failure remains detail-free.
