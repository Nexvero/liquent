# LQ-1457 Joint engine API operation-bound audit evidence

- Tests capture identities passed by both operation audit modes.
- Registry-only audit rejects acceptance replacement before inspection.
- Accepted-source audit rejects source and acceptance replacement.
- Same-content copies do not bypass descriptor identity checks.
- Prior failure-path and final revalidation tests remain green.
- Focused verification passes 93 tests under strict warnings.
- External image and staging evidence remains absent.
