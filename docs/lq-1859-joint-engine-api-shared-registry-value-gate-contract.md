# LQ-1859 Joint engine API shared registry value gate contract

- Operation and result constructor share one validator.
- Both require exact tuple and exact acceptance entries.
- No duplicated validator semantics may diverge.
- Operation gate limits downstream reads.
- Constructor gate protects direct result creation.
- Correlation remains a separate subsequent invariant.
- Failure semantics are identical at both boundaries.
