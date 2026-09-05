# LQ-1875 Joint engine API accept inventory failure contract

- Invalid inventory uses existing unavailable failure.
- No iteration or membership error escapes directly.
- Inventory object details never enter failure text.
- Pre-mutation failure leaves registry untouched.
- Post-mutation failure preserves durable marker state.
- Operation-root validation still closes each attempt.
- No new exception name is introduced.
