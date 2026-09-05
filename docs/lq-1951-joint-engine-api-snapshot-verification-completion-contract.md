# LQ-1951 Joint engine API snapshot verification completion contract

- Outer snapshot verification succeeds only with none completion.
- Any foreign return value fails closed.
- Verification exceptions remain authoritative failures.
- Completion check follows full snapshot verification.
- Retained snapshot remains the verified evidence.
- Failure remains detail-free.
- Public command behavior remains unchanged.
