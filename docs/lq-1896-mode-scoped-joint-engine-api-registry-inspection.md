# LQ-1896 Mode-scoped joint engine API registry inspection

- Registry value projections belong only to registry audit.
- Accepted-source audit consumes complete marker observations instead.
- Accepted mode never invokes the value inspection helper.
- Audit mode binding therefore governs projection access.
- Cross-mode result substitution remains rejected.
- No redundant registry projection is introduced.
- Existing mode behavior remains stable.
