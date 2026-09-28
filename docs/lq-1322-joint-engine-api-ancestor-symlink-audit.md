# LQ-1322 Joint engine API ancestor symlink audit

- Parent aliases cannot reach trusted source loading.
- The gate relies on no-follow descriptor opens at every boundary.
- It does not trust caller canonicalization or resolved path strings.
- Rejection precedes source bytes, provenance decoding, and verification.
- All descriptors acquired before failure remain locally closed.
- Focused ancestor and leaf regression evidence passes.
- No deployment or production-readiness assertion is introduced.
