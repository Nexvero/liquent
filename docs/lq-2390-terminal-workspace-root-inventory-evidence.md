# LQ-2390 Terminal workspace-root inventory evidence

- Focused tests prove the exact valid five-entry root inventory.
- They prove fail-closed additional, missing, and symbolic-link root entries.
- Existing workspace identity, evidence readback, private output-parent, and relative
  commit tests remain active.
- Fake gate adapters reproduce the same fixed root topology in orchestration tests.
- Production readiness remains false; artifact promotion and deployment are forbidden.
