# LQ-2040 Joint engine API audit root preflight

- Audit validates root after exact mode.
- Root validation precedes every UTC read.
- Root validation precedes every monotonic read.
- Root validation precedes descriptor work.
- Invalid input leaves persistence untouched.
- Both modes share the same root policy.
- Audit remains read-only.
