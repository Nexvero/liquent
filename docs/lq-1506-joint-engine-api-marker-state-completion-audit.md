# LQ-1506 Joint engine API marker state completion audit

- LQ-1495 through LQ-1505 close complete marker-state continuity.
- Audit and acceptance compare descriptor-derived immutable state.
- Same-inode rewrite with restored bytes fails both decision paths.
- Root, source, value, and timing checks remain independently required.
- Focused verification passes 52 tests under strict warnings.
- Full local verification passes 6390 tests with 108 PostgreSQL skips.
- Real image, Grype, and external run-signed evidence remain absent; production_ready=false.
