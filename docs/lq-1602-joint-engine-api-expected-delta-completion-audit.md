# LQ-1602 Joint engine API expected delta completion audit

- LQ-1591 through LQ-1601 close expected acceptance delta binding.
- Run ID and envelope digest derive from bound source evidence.
- Only that exact marker may explain acceptance state change.
- Inventory, root, source, marker, and timing checks remain required.
- Focused verification passes 45 tests under strict warnings.
- Full local verification passes 6446 tests with 108 PostgreSQL skips.
- Docker, Grype, and external run-signed evidence remain absent; production_ready=false.
