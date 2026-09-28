# LQ-2025 Joint engine API exact None gate

- Boolean false is not completion.
- Integer and float zero are not completion.
- Empty text and containers are not completion.
- Arbitrary objects are not completion.
- Equality cannot spoof None identity.
- Rejection uses existing unavailable failure.
- No new exception is named.
