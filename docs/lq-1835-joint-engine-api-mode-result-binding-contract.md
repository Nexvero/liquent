# LQ-1835 Joint engine API mode result binding contract

- Registry mode permits only exact registry audit result.
- Accepted-source mode permits only exact accepted audit result.
- Cross-mode closed results are rejected.
- Subclasses and foreign result forms are not accepted.
- Binding is enforced at success finalization entry.
- Invalid handoff fails before any result-specific reread.
- Public output remains unchanged.
