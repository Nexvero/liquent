# LQ-1891 Joint engine API validated registry inspection contract

- Every operation-level registry inspection crosses one validator.
- Validation occurs immediately after inspection return.
- Exact tuple and exact acceptance entry types apply.
- Malformed values fail before equality decisions.
- All inspections remain bound to resolved registry identity.
- Failure remains detail-free.
- Public registry audit behavior remains unchanged.
