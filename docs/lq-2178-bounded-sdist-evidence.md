# LQ-2178 Bounded sdist evidence

- Tests cover excessive count, name, file, and aggregate size.
- Negative and inconsistent size declarations fail closed.
- Symlink inputs are rejected without following their target.
- The real repository sdist remains below every fixed bound.
- Reproducible output and safe topology checks remain composed.
- No network, signing, upload, container, or deployment step is added.
- Production readiness still requires external release evidence.
