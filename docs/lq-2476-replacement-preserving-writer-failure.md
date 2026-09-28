# LQ-2476 Replacement-preserving writer failure

- Write failure enters cleanup with the originally created file identity.
- If another file now occupies the evidence name, its different inode is preserved.
- The writer still reports one detail-limited controlled-preflight rejection.
- The unlinked original open file closes through normal descriptor cleanup.
- No ownership claim is inferred from a matching name, owner, mode, or bytes.
- Existing caller data is never overwritten to restore writer state.
