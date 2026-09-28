# LQ-2249 sdist gzip trailer and size gate

- Gzip expansion is capped at forty MiB before TAR interpretation.
- A stream exceeding that limit is rejected without acceptance fallback.
- Successful expansion must consume one complete valid gzip member.
- The recorded CRC32 must equal the expanded TAR byte checksum.
- The recorded ISIZE must equal the expanded TAR size modulo 2^32.
- Corrupt, truncated, concatenated, or inconsistent envelopes fail closed.
- The bound adds no archive extraction or filesystem-write behavior.
