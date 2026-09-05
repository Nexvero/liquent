# LQ-2292 quality-evidence digest capture gate

- Capture requires both successful test categories and PostgreSQL identity.
- Passed counts must be positive integers.
- Warning counts must be nonnegative integers for each test run.
- PostgreSQL version must retain the existing restricted syntax.
- Canonical JSON of the validated facts is hashed with SHA-256.
- Capture occurs after PostgreSQL testing and before distributions.
- Callers cannot supply or override the resulting digest.
