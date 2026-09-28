# LQ-2362 Private directory-identity evidence

- Focused tests prove acceptance of a private mode-0700 directory identity.
- They prove fail-closed permission drift and symbolic-link rejection.
- A source-boundary test proves directory-only no-follow opening and descriptor
  metadata measurement while excluding the former `lstat` path snapshot.
- All downstream candidate-boundary tests remain active.
- Production readiness remains false; publication and promotion remain separate.
