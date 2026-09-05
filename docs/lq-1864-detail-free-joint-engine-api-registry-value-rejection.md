# LQ-1864 Detail-free joint engine API registry value rejection

- Explicit validation avoids incidental runtime failures.
- Null and arbitrary objects are externally indistinguishable.
- Foreign entries receive no partial trust.
- Rejection occurs at one deterministic boundary.
- No acceptance, run, marker, or path detail is disclosed.
- Existing technical unavailability remains sufficient.
- Command observability remains stable.
