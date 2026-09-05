# LQ-1984 Detail-free joint engine API UTC rejection

- Immediate UTC validation makes rejection deterministic.
- Null and arbitrary times are externally indistinguishable.
- Non-UTC values receive no partial trust.
- No timestamp, timezone, source, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
