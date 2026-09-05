# LQ-2406 Installed-wheel tree evidence

- Focused tests prove normalization followed by an identical terminal measurement.
- They prove private directory and file modes after normalization.
- They prove mode and symbolic-link drift fail closed and additional file content
  changes the canonical tree identity.
- Existing entry-point loading, root inventory, and bundle-gate checks remain active.
- Production readiness remains false; deployment and publication remain forbidden.
