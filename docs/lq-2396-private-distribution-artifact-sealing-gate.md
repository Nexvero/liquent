# LQ-2396 Private distribution-artifact sealing gate

- After deterministic sdist normalization, wheel and sdist are set to mode 0600.
- Terminal inventory accepts only current-user-owned regular files with that mode,
  exactly one link, non-zero size, and the existing local artifact size ceiling.
- Files are opened relative to the private artifacts descriptor without following links.
- Hashing and byte counting use the same open descriptor.
- Invalid metadata is rejected without repair at the terminal gate.
