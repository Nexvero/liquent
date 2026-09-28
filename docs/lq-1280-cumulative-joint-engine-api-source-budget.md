# LQ-1280 Cumulative joint engine API source budget

- The descriptor-relative loader counts each successfully read child value.
- Accumulation follows the fixed canonical source order.
- Equality with the 64 MiB ceiling remains admissible.
- The first byte beyond the ceiling rejects the complete operation.
- Declared file limits are not substituted for observed loaded lengths.
- Ten-, eleven-, and fourteen-source loaders share the same mechanism.
- Existing ownership, mode, link, and stability checks remain unchanged.
