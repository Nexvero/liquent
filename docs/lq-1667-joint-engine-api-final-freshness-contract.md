# LQ-1667 Joint engine API final freshness contract

- Retained source must remain valid at final wall time.
- Initial or inner validity alone is insufficient.
- Final time follows all success reobservations.
- The same retained snapshot is verified again.
- Policy freshness limits remain authoritative.
- Caller cannot supply a freshness decision.
- Expiration fails detail-free.
