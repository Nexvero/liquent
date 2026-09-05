# LQ-1512 State-bound joint engine API one-shot source

- One-shot captures a complete source observation before verification.
- It reloads the complete observation after durable marker record.
- Equality includes snapshot, root state, and all child states.
- Temporary rewrite followed by byte restoration is rejected.
- Marker generation and timing checks remain independently required.
- Expected source identity constrains both observations.
- CLI behavior remains unchanged.
