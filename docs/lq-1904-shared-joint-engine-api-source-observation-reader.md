# LQ-1904 Shared joint engine API source observation reader

- One helper composes source observation and type validation.
- It returns only exact run-bound source observations.
- Raw observer output never reaches operation logic.
- Source-root identity is mandatory on every call.
- No fallback unbound read is available.
- Existing observer remains source evidence authority.
- No new port or persistence model is introduced.
