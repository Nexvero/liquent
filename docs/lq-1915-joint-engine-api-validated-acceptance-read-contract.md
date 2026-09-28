# LQ-1915 Joint engine API validated acceptance read contract

- Every operation-level target marker read crosses one validator.
- Validation occurs immediately after observer return.
- Runtime type must be exact acceptance observation type.
- Missing or malformed marker fails before comparison.
- Reads remain bound to run and registry identity.
- Failure remains detail-free.
- Public command behavior remains unchanged.
