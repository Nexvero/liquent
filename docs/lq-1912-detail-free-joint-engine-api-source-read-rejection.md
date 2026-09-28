# LQ-1912 Detail-free joint engine API source read rejection

- Immediate exact-type validation makes rejection deterministic.
- Null and arbitrary returns are externally indistinguishable.
- Foreign source objects receive no partial trust.
- No authority, envelope, root, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
