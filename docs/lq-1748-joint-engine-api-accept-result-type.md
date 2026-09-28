# LQ-1748 Joint engine API accept result type

- Result contains source observation and registry observations.
- Source must be the exact run-bound observation type.
- Registry must be an exact tuple.
- Every registry member must be a marker observation.
- Fields are frozen and slot-backed.
- No mutation API or serialization exists.
- Representation is redacted.
