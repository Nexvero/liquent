# LQ-1481 Joint engine API operation marker stability evidence

- Focused tests cover observation, audit, and operation dependencies.
- Same-content marker replacement is rejected inside accepted audit.
- Stable-marker and value-only compatibility paths remain green.
- Root replacement and marker mutation regressions remain covered.
- No acceptance marker is modified by the read-only audit itself.
- Focused verification passes 72 tests under strict warnings.
- External image and staging evidence remains absent.
