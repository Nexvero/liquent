# LQ-1485 Joint engine API recorded marker observation evidence

- Tests match returned acceptance with the requested canonical value.
- Returned identity matches the durable marker filesystem identity.
- Bound record continues accepting the exact registry identity.
- Existing failure-window and cleanup tests remain green.
- Existing callers that discard the result remain compatible.
- Redacted observation representation remains inherited.
- Evidence is local and deterministic.
