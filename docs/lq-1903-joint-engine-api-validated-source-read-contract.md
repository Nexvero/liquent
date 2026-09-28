# LQ-1903 Joint engine API validated source read contract

- Every operation-level source read crosses one validator.
- Validation occurs immediately after observer return.
- Runtime type must be exact source observation type.
- Malformed source fails before snapshot field access.
- All reads remain bound to resolved source identity.
- Failure remains detail-free.
- Public command behavior remains unchanged.
