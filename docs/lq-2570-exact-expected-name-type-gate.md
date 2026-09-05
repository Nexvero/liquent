# LQ-2570 Exact expected-name type gate

- Every snapshotted expected key must have exact string runtime type.
- Boolean, integer, enum-like, and custom equality substitutes are rejected.
- Exact type validation precedes fixed-vocabulary set membership.
- A nonstring key cannot alias a valid phase-output name.
- Rejection occurs before workspace opening and descriptor creation.
- No key is coerced, normalized, or converted to text.
