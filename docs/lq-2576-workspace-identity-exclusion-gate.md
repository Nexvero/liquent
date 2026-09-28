# LQ-2576 Workspace-identity exclusion gate

- The validated workspace tuple is compared with every expected child tuple.
- Any equality rejects the complete expected mapping.
- The comparison follows child-shape and child-uniqueness validation.
- Empty expected state satisfies exclusion without inferred child facts.
- No path, descriptor, stat result, or callback participates in the decision.
- The original caller-owned mapping remains unmodified.
