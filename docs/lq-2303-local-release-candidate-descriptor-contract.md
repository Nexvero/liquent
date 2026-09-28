# LQ-2303 local release-candidate descriptor contract

- One `release-candidate.json` represents the terminal local candidate facts.
- It resides beside the verified bundle in the private output directory.
- Its bytes are canonical JSON with no self-referential digest field.
- SHA-256 of the complete descriptor bytes is the candidate identity.
- The descriptor contains no secrets, host paths, or caller authority.
- Existing bundle and verification artifacts remain unchanged.
- The descriptor is non-promotable local evidence only.
