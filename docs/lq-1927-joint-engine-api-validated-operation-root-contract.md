# LQ-1927 Joint engine API validated operation root contract

- Every operation-level root resolution crosses one type gate.
- Runtime type must be exact operation-roots value.
- Malformed resolver output fails before field access.
- Initial validation precedes all operation work.
- Post-operation validation precedes success checks.
- Failure remains detail-free.
- Public command behavior remains unchanged.
