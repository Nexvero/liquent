# LQ-1953 Joint engine API snapshot time binding

- Helper receives retained snapshot and explicit UTC instant.
- Both values pass unchanged to snapshot verifier.
- Verification result cannot substitute another snapshot.
- Caller-provided success boolean is not accepted.
- Existing freshness policy remains authoritative.
- Completion validation does not alter decision time.
- Failure remains detail-free.
