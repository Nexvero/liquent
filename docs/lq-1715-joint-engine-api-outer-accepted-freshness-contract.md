# LQ-1715 Joint engine API outer accepted freshness contract

- Accepted-source audit captures outer initial UTC.
- Final UTC follows all outer evidence rechecks.
- Final UTC may not precede initial UTC.
- Retained source must remain valid at final UTC.
- Inner final validity alone is insufficient.
- Caller cannot provide a freshness decision.
- Expiration fails detail-free.
