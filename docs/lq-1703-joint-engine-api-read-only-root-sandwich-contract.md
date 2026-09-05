# LQ-1703 Joint engine API read-only root sandwich contract

- Read-only audit resolves operation roots before work.
- It resolves the same roots again after inner success.
- Both complete root snapshots must compare exactly equal.
- No acceptance state change is permitted.
- Root, source, and acceptance generations remain fixed.
- Caller paths cannot replace resolved child paths.
- Mismatch fails unavailable.
