# LQ-1292 Remaining-budget joint engine API source reader

- Ordered loading computes remaining bytes immediately before each child.
- The common loader passes that remainder into the existing child bound.
- Existing per-file limits continue to win when they are stricter.
- A truncated allowance makes an oversized child fail closed while reading.
- No complete overflowing child is retained before aggregate rejection.
- Descriptor ownership, metadata comparison, and closure remain local.
- Successful canonical source sets preserve their existing representation.
