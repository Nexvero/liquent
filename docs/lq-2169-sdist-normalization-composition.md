# LQ-2169 sdist normalization composition

- Normalization runs immediately after the isolated distribution build.
- The recorded sdist hash therefore covers normalized bytes.
- Later sdist inspection consumes that same immutable artifact.
- Wheel generation and verification remain unchanged.
- No source tree file is rewritten by normalization.
- Temporary output is atomically installed within the private build area.
- Build failure and normalization failure remain detail-limited rejection.
