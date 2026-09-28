# LQ-1459 Joint engine API one-shot acceptance read contract

- One-shot acceptance binds every marker read to one registry identity.
- The identity is resolved outside the inner acceptance decision.
- Duplicate precheck and final readback consume the same fact.
- Neither read may adopt a replacement registry at the same path.
- Registry identity remains independent from source identity.
- Mismatch fails closed through the existing unavailable boundary.
- Direct unbound one-shot use remains supported.
