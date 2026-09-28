# LQ-1888 Detail-free joint engine API registry read rejection

- Immediate validation makes rejection deterministic.
- Null and arbitrary returns are externally indistinguishable.
- Foreign observations receive no partial trust.
- No run, marker, source, root, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
