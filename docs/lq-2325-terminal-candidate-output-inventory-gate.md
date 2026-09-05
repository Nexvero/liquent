# LQ-2325 Terminal candidate output inventory gate

- The bundle gate evaluates the inventory only after all three candidate files
  have been created and individually verified.
- It revalidates the private output directory and compares the enumerated names
  with the exact expected set.
- It rejects non-regular entries and verifies every current file digest.
- The resulting inventory digest is emitted as measured bundle-gate evidence.
- No later promotion decision is introduced by this terminal local check.
