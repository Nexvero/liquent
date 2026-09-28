# LQ-1554 Joint engine API marker invariant completion audit

- LQ-1543 through LQ-1553 close marker-state semantics.
- Type, owner, mode, link, identity, and exact size are enforced.
- Forged observations cannot become accept or audit evidence.
- Registry, source, generation, and timing checks remain required.
- Focused verification passes 39 tests under strict warnings.
- Full local verification passes 6417 tests with 108 PostgreSQL skips.
- Real image, Grype, and external run-signed evidence remain absent; production_ready=false.
