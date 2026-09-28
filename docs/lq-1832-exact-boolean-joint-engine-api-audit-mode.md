# LQ-1832 Exact boolean joint engine API audit mode

- Type identity rather than truthiness governs selection.
- Zero and one are not accepted as booleans.
- Null, strings, and objects are rejected.
- Validation occurs before any clock or filesystem read.
- Invalid mode cannot choose an operation branch.
- Existing unavailable failure remains authoritative.
- No new public enum is introduced.
