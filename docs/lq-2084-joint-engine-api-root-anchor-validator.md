# LQ-2084 Joint engine API root anchor validator

- Existing root validator owns anchor policy.
- Accepted anchor is the exact string slash.
- Anchor is inspected without filesystem I/O.
- Accepted Path is returned unchanged.
- No path normalization is performed.
- Existing unavailable failure is reused.
- No public port is added.
