# LQ-1545 Joint engine API marker type and owner invariants

- Directory state cannot masquerade as marker evidence.
- Regular-file state is required at value construction.
- Foreign ownership is rejected.
- Exact owner-private mode remains mandatory.
- Descriptor-derived observations already satisfy these facts.
- Forged state fails before comparison use.
- Failure reveals no marker metadata.
