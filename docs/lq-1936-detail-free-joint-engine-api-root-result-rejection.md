# LQ-1936 Detail-free joint engine API root result rejection

- Immediate exact-type validation makes rejection deterministic.
- Null and arbitrary returns are externally indistinguishable.
- Foreign root values receive no partial trust.
- No identity, state, root, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
