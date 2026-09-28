# LQ-2233 Wheel member-set digest gate

- Sorted member names form a newline-terminated canonical sequence.
- Release preflight requires exactly 422 unique members.
- SHA-256 binds the complete canonical sequence.
- Count and digest must be supplied together by trusted composition.
- Standalone verification still enforces root and top-level policy.
- Direct and sdist-roundtrip wheels receive the same release facts.
- No caller-derived allowlist is accepted by preflight composition.
