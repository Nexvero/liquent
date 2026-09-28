# LQ-2297 cross-bundle verification-evidence gate

- Bundle construction receives the captured verification file path.
- The operational manifest independently records its digest and size.
- Bundle verification checks the embedded evidence bytes and schema.
- The local gate then rereads the source evidence and rechecks its digest.
- Mutation before or during bundle construction therefore fails closed.
- Successful phase facts expose the captured verification SHA-256.
- Neither source evidence nor bundle is made promotable by this check.
