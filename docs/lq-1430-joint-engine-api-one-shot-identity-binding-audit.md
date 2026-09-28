# LQ-1430 Joint engine API one-shot identity binding audit

- One-shot write identity now has an explicit operation-owned path.
- The binding is not inferred again after operation-root resolution.
- Durable record remains the sole enforcement point for opened identity.
- Existing precheck and unknown-outcome semantics remain unchanged.
- Compatibility callers retain their established standalone behavior.
- Focused forwarding and regression evidence passes.
- No broader operation-root API is exposed.
