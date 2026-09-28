# LQ-1517 Joint engine API audit source state evidence

- Tests rewrite and restore one source child during audit.
- Snapshot bytes and inode return to their original values.
- Changed descriptor state still causes fail-closed rejection.
- Stable source allows acceptance followed by audit.
- Marker-state and root-binding regressions remain green.
- Focused verification passes 60 tests under strict warnings.
- External runtime evidence remains absent.
