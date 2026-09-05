# LQ-1957 Joint engine API snapshot completion evidence

- Tests reject foreign direct verifier completion.
- Accept invokes two shared completion checks.
- Foreign completion at either accept stage is rejected.
- Durable marker remains after rejection.
- Accepted audit invokes one outer completion check.
- Foreign accepted-audit completion is rejected.
- All focused warnings are treated as errors.
