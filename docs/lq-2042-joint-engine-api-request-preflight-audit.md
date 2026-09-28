# LQ-2042 Joint engine API request preflight audit

- Caller shape is separated from persisted authority.
- Shape validation grants no filesystem trust.
- Root resolution remains the system-of-record check.
- No caller-supplied mode implies capability.
- No invalid request consumes clock budget.
- Existing direct completion remains exact None.
- No durable layout changes.
