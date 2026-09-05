# LQ-1496 Joint engine API marker state value

- Observation adds one immutable nine-field marker-state tuple.
- Each field must be an exact nonnegative integer.
- Boolean, textual, list, short, and identity-mismatched state fails.
- Observation equality now includes the complete marker state.
- Acceptance value and marker identity remain separately accessible.
- Existing redacted representation is unchanged.
- No persistence schema or serialized format is introduced.
