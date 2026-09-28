# LQ-2036 Shared joint engine API root argument validator

- One private validator closes direct root arguments.
- It performs no filesystem operation.
- It performs no clock read.
- It returns the accepted Path unchanged.
- It performs no normalization.
- It reuses unavailable failure.
- No public port is added.
