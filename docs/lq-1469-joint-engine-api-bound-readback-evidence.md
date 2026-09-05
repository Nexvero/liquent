# LQ-1469 Joint engine API bound readback evidence

- Tests replace the registry after the original durable record.
- The replacement copies the same canonical marker bytes and modes.
- Bound final readback rejects the replacement root identity.
- Earlier duplicate, write, source, and final checks remain green.
- Operation-root revalidation remains an independent outer defense.
- Focused verification passes 84 tests under strict warnings.
- External image and staging evidence remains absent.
