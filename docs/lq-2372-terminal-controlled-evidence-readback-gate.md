# LQ-2372 Terminal controlled-evidence readback gate

- Immediately before the commit boundary, the private workspace and fixed evidence
  name are reopened with directory-only and no-follow semantics.
- Evidence must be a current-user-owned mode-0600 regular file with one link and the
  exact expected size.
- Persisted bytes are read through that descriptor and must equal the canonical
  in-memory evidence payload.
- No path-based read or alternate evidence source is accepted.
