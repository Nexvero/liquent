# LQ-1933 Joint engine API validated root result evidence

- Tests reject three malformed initial root results.
- Initial rejection occurs before operation work.
- Accept performs two validated root resolutions.
- Read-only audit performs two validated resolutions.
- Malformed second result rejects both operation modes.
- Durable accept marker remains preserved on rejection.
- All focused warnings are treated as errors.
