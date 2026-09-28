# LQ-1885 Joint engine API validated registry read evidence

- Tests observe shared-reader use in all three operations.
- Accept invokes four validated registry reads.
- Each audit mode invokes three validated registry reads.
- Malformed terminal reads fail in every operation.
- Tests preserve original bound acceptance-root identity.
- Earlier validator-call expectations are updated.
- All focused warnings are treated as errors.
