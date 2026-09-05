# LQ-1879 Joint engine API validated registry read contract

- Every operation-level registry read crosses one validator.
- Validation occurs immediately after observer return.
- Exact tuple, observation types, order, and uniqueness apply.
- Malformed reads fail before equality or delta decisions.
- All reads remain bound to the resolved registry identity.
- Failure remains detail-free.
- Public command behavior remains unchanged.
