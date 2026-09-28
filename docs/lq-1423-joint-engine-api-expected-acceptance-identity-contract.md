# LQ-1423 Joint engine API expected acceptance identity contract

- Operation-bound writes carry the resolved acceptance-root identity.
- The expected value contains exactly nonnegative device and inode facts.
- Record compares it with the descriptor it actually opens.
- Mismatch fails before canonical marker creation begins.
- Identity is an internally resolved fact, never an allow decision.
- Malformed identity values fail closed without registry side effects.
- Standalone record behavior remains available without operation binding.
