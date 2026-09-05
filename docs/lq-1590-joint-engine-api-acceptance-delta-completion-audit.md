# LQ-1590 Joint engine API acceptance delta completion audit

- LQ-1579 through LQ-1589 close acceptance-directory delta binding.
- Exactly one canonical marker explains intended state change.
- Missing, malformed, unrelated, or destructive deltas fail.
- Root, source, marker, identity, and timing checks remain required.
- Focused verification passes 57 tests under strict warnings.
- Full local verification passes 6442 tests with 108 PostgreSQL skips.
- Docker, Grype, and external run-signed evidence remain absent; production_ready=false.
