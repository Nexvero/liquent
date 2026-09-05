# LQ-1377 Joint engine API acceptance root component evidence

- Tests exercise marker load, registry inspection, and marker record.
- Every operation rejects a symlinked parent component.
- Existing leaf-symlink and private-mode evidence remains green.
- A real unchanged component chain supports all three operations.
- Marker operations retain descriptor-relative child access.
- Existing acceptance failure-window tests remain green.
- Focused verification treats deprecation warnings as failures.
