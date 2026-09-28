# LQ-1320 Pre-source joint engine API ancestor symlink gate

- No-follow directory opens execute once for every ancestor segment.
- The operating system rejects a symlink before traversal can continue.
- No source-root inventory or child open follows that rejection.
- The same mechanism covers leaf symlinks without a separate fallback.
- Descriptor closure applies on both successful and rejected traversal.
- No canonicalization, retry, or target-path substitution is attempted.
- All source-set loaders use the shared gate.
