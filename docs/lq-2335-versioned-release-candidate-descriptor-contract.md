# LQ-2335 Versioned release-candidate descriptor contract

- The local release-candidate descriptor declares schema version 1.
- The schema version participates in canonical descriptor facts and therefore in
  the release-candidate SHA-256 identity.
- Unknown future representations cannot be treated as this version implicitly.
- Versioning changes no publication, promotion, or compatibility policy.
- The descriptor remains local, immutable evidence and non-promotable.
