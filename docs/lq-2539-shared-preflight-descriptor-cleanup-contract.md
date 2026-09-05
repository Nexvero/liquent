# LQ-2539 Shared preflight descriptor-cleanup contract

- Intermediate verification and phase-output capture share one cleanup rule.
- Every supplied descriptor receives exactly one close attempt in given order.
- A failed close does not prevent later descriptors from being processed.
- Any failure produces only the existing controlled preflight rejection.
- The cleanup helper owns no filesystem lookup or destructive operation.
- Cleanup success grants no publication, deployment, or release authority.
