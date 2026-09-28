# LQ-2404 Private installed-wheel tree normalization gate

- Tree measurement starts only after all installed entry points load successfully.
- Traversal opens each child relative to its parent descriptor without following links.
- Current-user-owned directories are normalized to 0700 and singly linked regular
  files to 0600 before their terminal identity is retained.
- File bytes are hashed through the same stable descriptor used for metadata checks.
- Directory entry sets are checked before and after recursive traversal.
