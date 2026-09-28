# LQ-2145 Joint engine API Unicode control gate

- Every Unicode Cc character is rejected.
- Existing ASCII control rejection is subsumed.
- Non-ASCII controls are equally rejected.
- Control position does not change rejection.
- No escaping or replacement occurs.
- No control reaches Path construction.
- No diagnostic detail is exposed.
