# LQ-2156 Shared joint engine API root text validator

- One private validator owns root text policy.
- It performs no Path construction.
- It performs no filesystem operation.
- It performs no clock read.
- It returns accepted string identity.
- It reuses unavailable failure.
- No public port is added.
