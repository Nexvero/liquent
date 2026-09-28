# LQ-1503 Joint engine API recorded marker state contract

- One-shot acceptance retains complete state from durable record.
- Final observation must equal recorded value, identity, and state.
- A same-inode rewrite after record invalidates the outcome.
- Byte restoration cannot restore recorded status-change time.
- Registry and source root identities remain separate requirements.
- Failure exposes no marker state or filesystem detail.
- No rollback is attempted after a durable but invalidated record.
