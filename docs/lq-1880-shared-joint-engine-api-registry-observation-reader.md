# LQ-1880 Shared joint engine API registry observation reader

- One helper composes observer and inventory validator.
- It returns only a validated canonical observation tuple.
- Raw observer output never reaches operation logic.
- Acceptance-root identity is mandatory on every call.
- No fallback unbound read is available.
- Existing observer remains the filesystem authority.
- No new port or persistence model is introduced.
