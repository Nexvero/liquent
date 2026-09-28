# LQ-2505 Prephase bound directory-set gate

- Every phase begins with the complete retained identity mapping.
- The gate rejects missing, additional, replaced, linked, or non-private entries.
- No trusted phase executes after loss of any captured directory identity.
- Empty initial state is represented by an empty mapping, not inferred absence.
- Caller-controlled names or identities cannot extend the expected set.
- Later phase output cannot repair an earlier continuity failure.
