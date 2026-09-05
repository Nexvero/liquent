# LQ-2162 Joint engine API shared root text audit

- CLI and direct paths cannot diverge on text policy.
- No direct Path bypasses Unicode policy.
- No direct Path bypasses byte bounds.
- No invalid rendered text reaches authority checks.
- Exact native type remains the first direct gate.
- Existing completion policy remains authoritative.
- No durable layout changes.
