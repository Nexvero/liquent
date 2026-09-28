# LQ-1521 Joint engine API source convergence evidence

- Tests observe two opens for representative fixed-layout children.
- Content change between passes is rejected.
- Mode change between passes is rejected.
- Stable children produce the established snapshot.
- Budget and path-binding regressions remain green.
- No marker is created after initial convergence failure.
- Evidence is local and deterministic.
