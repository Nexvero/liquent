# LQ-1473 Descriptor-bound joint engine API marker observation

- Observation reads and validates one no-follow marker descriptor.
- Its pre-read descriptor facts supply marker identity.
- Stable metadata and exact byte count remain required after reading.
- Registry identity may independently constrain the containing root.
- Visible-root validation remains mandatory before returning.
- Missing marker returns neutral absence without fabricated identity.
- No path-based post-read stat becomes the evidence source.
