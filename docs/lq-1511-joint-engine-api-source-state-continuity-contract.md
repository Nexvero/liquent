# LQ-1511 Joint engine API source state continuity contract

- One decision must consume one unchanged source observation.
- Snapshot, root state, and every child state must compare equal.
- Same inode and restored bytes cannot hide intervening mutation.
- Source continuity remains independent from marker continuity.
- Any state mismatch invalidates the decision.
- Failure exposes no changed path or metadata.
- No repair or retry is performed.
