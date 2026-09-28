# LQ-1869 Post-mutation joint engine API inventory gate

- Final registry observation crosses the same exact gate.
- Validation occurs immediately after observation.
- Invalid final inventory cannot enter delta calculation.
- Invalid final inventory cannot enter result construction.
- A potentially durable marker is not deleted on failure.
- Existing unknown-outcome semantics remain intact.
- No hidden retry or cleanup is introduced.
