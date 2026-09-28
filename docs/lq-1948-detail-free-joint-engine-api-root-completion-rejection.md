# LQ-1948 Detail-free joint engine API root completion rejection

- Exact none checking makes completion deterministic.
- Arbitrary return values are externally indistinguishable.
- Foreign completion receives no partial trust.
- No identity, state, root, or path detail escapes.
- Technical unavailability remains the only failure form.
- No additional logging surface is introduced.
- Command observability remains stable.
