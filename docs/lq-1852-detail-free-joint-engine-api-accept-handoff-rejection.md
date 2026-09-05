# LQ-1852 Detail-free joint engine API accept handoff rejection

- Explicit type validation avoids incidental runtime errors.
- Null and arbitrary objects are indistinguishable externally.
- Bare acceptance values receive no partial trust.
- Rejection occurs at one deterministic boundary.
- No marker, path, run, or source detail is disclosed.
- Existing technical unavailability remains sufficient.
- Command observability remains stable.
