# LQ-2340 No-follow candidate-descriptor read gate

- `release-candidate.json` is opened relative to the bound parent and without
  following symbolic links.
- The opened object must be a mode-0600 regular file owned by the current user,
  with exactly one link and exactly the canonical expected size.
- Oversized or structurally invalid descriptors are rejected before acceptance.
- Hashing and byte comparison use only that open descriptor.
- Technical rejection remains detail-free at the existing gate boundary.
