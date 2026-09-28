# LQ-1740 Correlated joint engine API registry result

- Operation constructs result from two bound registry reads.
- Constructor derives value tuple from observation acceptances.
- Exact equality is required against inspected values.
- Empty registry constructs one valid empty result.
- Outer rereads compare named fields directly.
- No tuple index or tag parsing remains.
- Mismatch raises unavailable.
