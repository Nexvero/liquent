# LQ-2585 Coherent phase-boundary order

- Order is pre-verifier, one gate execution, optional capture, post-verifier.
- Workspace identity checks continue immediately around gate execution.
- No redundant retained-child callback splits either map verification result.
- Receipt bytes remain opaque until the complete post-verifier succeeds.
- Controller state changes only through fixed mapped output capture.
- Every rejection still prevents successful evidence publication.
