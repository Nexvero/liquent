# LQ-1988 Shared joint engine API monotonic validator

- One private validator closes all outer reads.
- It returns the exact accepted value unchanged.
- It performs no clock read itself.
- It has no persistence effect.
- It introduces no normalization.
- It reuses unavailable failure.
- It introduces no exception name.
