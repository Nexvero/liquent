# LQ-2403 Bounded installed-wheel tree contract

- The installed-wheel tree is bounded to 32 levels, 1024 directories, 4096 files,
  8 MiB per file, and 64 MiB total file bytes.
- Every path component is non-empty, slash-free, and at most 255 encoded bytes.
- Only real directories and regular files are accepted; empty package markers remain valid.
- Symbolic links, special files, excessive shape, or excessive bytes fail closed.
- The tree remains local entry-point evidence, not a deployable installation.
