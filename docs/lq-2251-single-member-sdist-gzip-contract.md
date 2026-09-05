# LQ-2251 single-member sdist gzip contract

- A normalized sdist contains exactly one gzip member.
- That member expands to exactly one canonical TAR byte stream.
- Concatenated members are not an accepted extension mechanism.
- Bytes after the first member are rejected even when independently valid.
- The bounded expansion check runs before single-member acceptance.
- Header and trailer requirements from LQ-2247 remain unchanged.
- This contract adds no extraction or publication authority.
