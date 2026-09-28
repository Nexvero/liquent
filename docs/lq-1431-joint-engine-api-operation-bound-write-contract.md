# LQ-1431 Joint engine API operation bound write contract

- `accept-once` binds write authority to its resolved acceptance child.
- The immutable operation-root value owns the expected child identity.
- The inner one-shot call receives exactly that device and inode pair.
- Replacement between outer resolution and inner record fails closed.
- Neither old nor replacement registry receives a marker on mismatch.
- Outer finalization remains mandatory after inner failure.
- Audit modes remain read-only and require no write identity.
