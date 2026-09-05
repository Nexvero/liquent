# LQ-1279 Joint engine API source budget contract

- A complete staging source snapshot has one fixed 64 MiB byte budget.
- The bound applies to bytes actually loaded across the complete source set.
- Existing stricter per-source bounds remain independently authoritative.
- The caller cannot select, enlarge, or disable the aggregate bound.
- Exceeding either kind of bound fails closed as technical unavailability.
- No partial provenance snapshot becomes observable after rejection.
- This slice introduces no deployment-readiness claim.
