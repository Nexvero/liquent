# LQ-2400 Private roundtrip-wheel sealing gate

- The rebuilt wheel is set to mode 0600 before phase success is recorded.
- Terminal inventory accepts only a current-user-owned regular file with that mode,
  one link, non-zero size, and the existing local artifact size ceiling.
- It is opened relative to the private roundtrip directory without following links.
- Hashing and byte counting use the same stable descriptor.
- Invalid metadata or bytes fail closed without repair.
