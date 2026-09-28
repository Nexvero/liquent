# LQ-1867 Joint engine API accept inventory handoff contract

- Accept operation validates both registry inventory handoffs.
- Before inventory is validated prior to mutation.
- After inventory is validated prior to delta calculation.
- Both require exact canonical observation tuples.
- Foreign or malformed inventories fail closed.
- No coercion or partial trust is permitted.
- Public accept-once behavior remains unchanged.
