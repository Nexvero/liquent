# LQ-2342 Bound candidate-descriptor evidence

- Focused tests retain canonical-byte and mode-drift coverage.
- They prove fail-closed rejection of symbolic-link and external-hardlink drift.
- A source-boundary test proves directory-relative no-follow opening and excludes
  path-based descriptor reads.
- Existing atomic creation, size, digest, and inventory tests remain active.
- Production readiness remains false; publication and promotion remain separate.
