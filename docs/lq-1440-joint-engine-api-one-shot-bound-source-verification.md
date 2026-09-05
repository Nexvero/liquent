# LQ-1440 Joint engine API one-shot bound source verification

- One-shot verification forwards expected source identity to each load.
- Acceptance identity continues independently to durable marker record.
- No caller-supplied allow flag or role participates in either check.
- A mismatched source root fails through the existing unavailable result.
- Snapshot equality and final verification checks remain unchanged.
- Time bounds, readback, and marker durability remain mandatory.
- The command-line contract does not gain an identity argument.
