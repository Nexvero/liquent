# LQ-2171 sdist member topology contract

- Every archive member belongs to one relative package root.
- Absolute, parent, dot, empty-component, and backslash names fail closed.
- Duplicate member names are ambiguous and fail closed.
- A second top-level root is not accepted as package content.
- Validation precedes deterministic archive replacement.
- No extraction or filesystem traversal is performed by the gate.
- Publication and installation remain outside this contract.
