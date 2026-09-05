# LQ-1834 Joint engine API audit mode foundation

- One closed input bit selects one audit branch.
- Registry and accepted-source branches remain disjoint.
- Existing branch-specific evidence remains unchanged.
- Input validation precedes all branch-specific work.
- Failure uses the existing detail-free boundary.
- No signature, persistence, or CLI option changes.
- Mode foundation is ready for result binding.
