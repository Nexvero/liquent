# LQ-2284 source-bound pair-digest extension

- Canonical pair facts now include source commit and integer epoch.
- Existing wheel name, sdist name, version, and digests remain included.
- One canonical JSON serialization feeds the pair SHA-256.
- A change to any provenance or artifact fact changes the digest.
- Invalid commit syntax and invalid epoch bounds reject fail closed.
- Individual artifact digests retain their existing identities.
- No artifact payload or filename is modified by this extension.
