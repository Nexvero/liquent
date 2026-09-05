# LQ-1500 State-bound joint engine API marker audit

- Existing dual observation equality now includes marker state.
- Initial observation establishes canonical value and descriptor facts.
- Final observation must reproduce every immutable state field.
- Temporary rewrite followed by byte restoration is rejected.
- Registry identity and source identity checks remain unchanged.
- Cryptographic, temporal, and duration checks remain mandatory.
- The audit command interface is unchanged.
