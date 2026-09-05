# LQ-2131 Joint engine API bounded CLI root contract

- Raw CLI root must encode as UTF-8.
- Total encoded length is at most 4095 bytes.
- Each encoded component is at most 255 bytes.
- ASCII control characters are rejected.
- Bounds precede Path construction and dispatch.
- Rejection remains detail-free.
- Public option syntax remains unchanged.
