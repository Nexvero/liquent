# LQ-2143 Joint engine API canonical Unicode root contract

- Raw CLI root must already be exact NFC.
- Unicode control characters are rejected.
- Unicode format characters are rejected.
- Unicode surrogate characters are rejected.
- No normalization is performed for callers.
- Validation precedes Path construction and dispatch.
- Public option syntax remains unchanged.
