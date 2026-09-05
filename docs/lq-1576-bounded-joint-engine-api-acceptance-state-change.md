# LQ-1576 Bounded joint engine API acceptance state change

- Validator has an explicit accept-only state-change option.
- It substitutes only final acceptance state for equality comparison.
- Path, identity, root state, and source state remain fixed.
- Non-boolean option values fail closed.
- Accept wrapper opts in explicitly.
- Audit and generic wrappers retain strict default behavior.
- No arbitrary mutation allowance is introduced.
