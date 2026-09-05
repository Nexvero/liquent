# LQ-2276 canonical distribution-pair digest

- One canonical object binds both filenames, both digests, and version.
- Object keys and JSON encoding follow the existing canonical serializer.
- SHA-256 of that object is the distribution-pair identity.
- Individual artifact digests remain visible as separate measured facts.
- Changing either name, version, or byte stream changes the pair identity.
- The digest is captured only after source and metadata parity checks pass.
- No persisted registry or external attestation is introduced.
