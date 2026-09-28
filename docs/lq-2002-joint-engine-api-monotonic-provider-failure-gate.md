# LQ-2002 Joint engine API monotonic provider failure gate

- Outer monotonic reads use the shared reader.
- Existing monotonic provider ownership remains.
- Malformed values use the monotonic validator.
- Provider exceptions use unavailable failure.
- All operation stages inherit the gate.
- Duration sequencing is unchanged.
- No fallback clock exists.
