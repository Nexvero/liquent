# LQ-1498 Joint engine API marker state evidence

- Tests compare observation state with all marker descriptor facts.
- Device and inode prefix matches the exposed marker identity.
- Malformed and identity-inconsistent states are rejected.
- Recorded observation exposes post-sync marker timestamps.
- Stable marker loading remains compatible.
- Tests exercise observable state without serialization choices.
- Evidence remains local and deterministic.
