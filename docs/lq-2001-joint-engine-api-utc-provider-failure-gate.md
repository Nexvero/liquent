# LQ-2001 Joint engine API UTC provider failure gate

- Accept UTC uses the shared reader.
- Accepted-Audit UTC uses the shared reader.
- Each retains its existing provider ownership.
- Malformed values use the UTC validator.
- Provider exceptions use unavailable failure.
- Registry-Audit remains UTC-free.
- Wall-clock sequencing is unchanged.
