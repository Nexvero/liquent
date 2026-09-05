# LQ-1892 Shared joint engine API registry value reader

- One helper composes inspection and value validation.
- It returns only an exact acceptance tuple.
- Raw inspection output never reaches audit logic.
- Acceptance-root identity is mandatory on every call.
- No fallback unbound inspection is available.
- Existing inspector remains the projection authority.
- No new port or persistence model is introduced.
