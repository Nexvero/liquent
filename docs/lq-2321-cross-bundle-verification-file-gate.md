# LQ-2321 cross-bundle verification-file gate

- File verification requires the captured private-directory identity.
- Type, mode, owner, link count, size, bytes, and digest are checked.
- The first check occurs before report input reaches bundle construction.
- The second check occurs after bundle schema and integrity verification.
- Mutation across the bundle operation therefore fails closed.
- The embedded report remains independently checked by the bundle manifest.
- Verification repairs neither source report nor embedded bytes.
