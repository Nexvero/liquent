# LQ-2273 cross-phase distribution-pair gate

- One shared check rereads and hashes both current artifact paths.
- Wheel, sdist, and bundle phases invoke that same pair check.
- Both current digests must equal the build-phase captured identities.
- Wheel replacement blocks even a later sdist-only operation.
- sdist replacement blocks even a later wheel-only operation.
- Revocation by byte replacement therefore affects every later decision.
- Failure remains detail-limited and causes no artifact rewrite.
