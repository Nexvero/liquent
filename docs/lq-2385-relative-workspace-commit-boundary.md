# LQ-2385 Relative workspace commit boundary

- Workspace publication renames source and destination relative to one bound parent
  directory descriptor.
- The rename remains the final potentially failing publication operation.
- The signal commit boundary is entered immediately before that operation, preserving
  the rule that visible success cannot become an interruption rejection.
- No path-based `Path.replace` operation remains in publication.
- Publication still grants no artifact promotion or deployment authority.
