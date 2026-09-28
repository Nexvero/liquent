# LQ-2119 Joint engine API raw CLI root contract

- Raw CLI root is validated before Path conversion.
- Runtime input must be exact string.
- Spelling must use one leading slash.
- Every component must be explicit and nonempty.
- Trailing slash and NUL are rejected.
- Rejection precedes Namespace handoff.
- Public option name remains unchanged.
