# LQ-2236 Wheel source-tree enumerator

- Enumeration is restricted to src/liquent and src/liquent_platform.
- Only .py and .mako regular files are package payload candidates.
- Symlinked roots or candidate files fail closed.
- Source-relative paths use canonical POSIX spelling.
- Missing and additional source candidates are both rejected.
- The current reviewed set contains exactly 417 payload files.
- No tests, documentation, cache, or build output enters the set.
