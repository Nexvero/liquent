# LQ-2075 Joint engine API parse dispatch boundary

- Parsing produces one candidate Namespace.
- Validation closes its shape and values.
- Dispatcher receives only validated fields.
- Malformed handoff invokes no dispatcher.
- Root resolution remains downstream.
- Operation invocation remains downstream.
- No duplicate parser is introduced.
