# LQ-2377 Fixed-phase gate-receipt binding

- Receipt parsing accepts an expected phase only when it belongs to the fixed
  controlled-preflight phase inventory.
- The canonical document must still contain exactly the existing five keys.
- Embedded phase, status, schema version, commit, and facts digest retain their
  existing exact validations.
- A caller cannot use the parser to legitimize an unconfigured phase.
- Canonical byte equality remains mandatory after parsing.
