# LQ-1840 Composed joint engine API mode-bound audit

- Entry mode gate closes branch selection.
- Operation body creates branch-specific closed evidence.
- Success entry binds that evidence back to mode.
- Existing source, marker, registry, and time checks follow.
- Both modes preserve their independent convergence rules.
- No new read, mutation, or timing budget is added.
- Public CLI status remains stable.
