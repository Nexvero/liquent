# LQ-1604 Descriptor-bound joint engine API registry observation

- One held registry descriptor supplies names and marker opens.
- Every marker uses descriptor-relative no-follow observation.
- Complete marker state remains stable during its read.
- Registry metadata and name set remain stable during inventory.
- Visible-root validation remains mandatory.
- Empty registry returns an empty observation tuple.
- Existing value-only inspection remains compatible.
