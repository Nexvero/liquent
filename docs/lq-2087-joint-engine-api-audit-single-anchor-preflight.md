# LQ-2087 Joint engine API audit single anchor preflight

- Both Audit modes check exact root anchor.
- Anchor validation follows exact mode validation.
- It precedes UTC and monotonic reads.
- It precedes root resolution.
- Double-slash input leaves state untouched.
- Valid single-anchor input remains read-only.
- Signature remains unchanged.
