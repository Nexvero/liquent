# LQ-1436 Bound joint engine API run source loader

- The run-bound loader accepts an optional expected root identity.
- It validates the expected pair before trusting filesystem state.
- The opened directory descriptor supplies the authoritative identity.
- Same-content path replacement cannot satisfy the old identity.
- Existing owner, mode, layout, child, and revalidation checks remain.
- Failure uses the established detail-free unavailable boundary.
- No source mutation or identity discovery API is introduced.
