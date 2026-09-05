# LQ-1428 Joint engine API one-shot bound write

- One-shot verification accepts one keyword-only expected identity.
- The value remains unchanged through verification and marker construction.
- Durable record performs the actual descriptor identity comparison.
- Existing standalone callers may omit the operation-level binding.
- Operation-root callers always supply the resolved acceptance identity.
- Failure remains within the existing detail-free one-shot boundary.
- Public CLI arguments remain source root and acceptance root only.
