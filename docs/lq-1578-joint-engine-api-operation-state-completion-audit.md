# LQ-1578 Joint engine API operation state completion audit

- LQ-1567 through LQ-1577 close operation directory-state binding.
- Root and source remain exact across all decision modes.
- Acceptance change is narrowly permitted only for marker creation.
- Paths, identities, inner observations, and timing remain required.
- Focused verification passes 51 tests under strict warnings.
- Full local verification passes 6438 tests with 108 PostgreSQL skips.
- Real image, Grype, and external run-signed evidence remain absent; production_ready=false.
