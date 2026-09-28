# LQ-1924 Detail-free joint engine API acceptance read rejection

- Immediate exact-type validation makes rejection deterministic.
- Null and arbitrary returns are externally indistinguishable.
- Foreign marker objects receive no partial trust.
- No acceptance, run, root, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
