# LQ-1751 Joint engine API accept result correlation contract

- Result must contain source-derived acceptance exactly once.
- Expected run id comes only from retained authority.
- Expected envelope hash comes only from retained envelope bytes.
- Existing markers for other runs may remain present.
- Duplicate matching acceptance is forbidden.
- Caller expectations are never accepted.
- Correlation mismatch fails unavailable.
