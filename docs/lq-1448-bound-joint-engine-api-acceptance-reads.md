# LQ-1448 Bound joint engine API acceptance reads

- Single-marker load accepts an optional expected root identity.
- Whole-registry inspection accepts the same optional binding.
- Both validate the identity before trusting registry entries.
- Same-content directory replacement cannot inherit old identity.
- Existing owner, mode, file, layout, and revalidation checks remain.
- Failure uses the established detail-free unavailable boundary.
- No mutation, schema, or caller identity input is introduced.
