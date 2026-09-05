# LQ-1994 Joint engine API validated monotonic audit

- Outer clock use is now centrally observable.
- No raw outer monotonic result reaches arithmetic.
- Accept retains three bounded stages.
- Both audit modes retain three bounded stages.
- UTC and monotonic validation remain separate.
- Existing root closure still runs after failure.
- No durable format changes.
