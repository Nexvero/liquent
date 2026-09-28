# LQ-2006 Joint engine API clock failure audit

- No direct outer provider call bypasses the reader.
- No ordinary provider exception crosses the API boundary.
- Validator failures retain their established type.
- Clock values never appear in errors.
- Provider messages never appear as explicit causes.
- Existing timing counts remain stable.
- No durable state format changes.
