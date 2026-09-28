# LQ-2146 Joint engine API Unicode format gate

- Every Unicode Cf character is rejected.
- Zero-width formatting is rejected.
- Bidirectional controls are rejected.
- Byte-order marks are rejected.
- Visible ordering cannot be caller-altered invisibly.
- No format character reaches Path construction.
- No caller exception exists.
