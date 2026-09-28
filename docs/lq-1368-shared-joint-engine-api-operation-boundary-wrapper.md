# LQ-1368 Shared joint engine API operation boundary wrapper

- `accept_once` delegates verification and acceptance through the wrapper.
- Registry audit delegates read-only inspection through the same wrapper.
- Accepted-source audit delegates full verification through that wrapper.
- Mode-specific work remains represented by small internal callables.
- Shared finalization owns all operation-root revalidation.
- Return values cannot escape before successful boundary finalization.
- No new filesystem, persistence, or cryptographic primitive is added.
