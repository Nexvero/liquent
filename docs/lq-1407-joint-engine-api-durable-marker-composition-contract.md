# LQ-1407 Joint engine API durable marker composition contract

- Durable record composes exclusive creation, write, sync, and readback.
- Exact content and stable metadata jointly establish marker trust.
- Directory sync and visible-root validation follow marker trust.
- Every phase uses the originally held registry and marker descriptors.
- A failure in any phase rejects the complete record operation.
- No phase accepts caller-supplied success or stored-byte assertions.
- Existing one-shot acceptance remains the higher-level consumer.
