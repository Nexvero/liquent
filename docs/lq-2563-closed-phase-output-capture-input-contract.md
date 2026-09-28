# LQ-2563 Closed phase-output capture-input contract

- Phase-output capture validates all authority-bearing inputs before opening.
- Workspace identity must satisfy the exact filesystem-identity fact contract.
- Output name must be an exact string from the four fixed phase mappings.
- Invalid facts and unsupported names fail closed without filesystem access.
- No input is coerced, normalized, inferred, or replaced by a default.
- Input validity grants no publication, deployment, or release authority.
