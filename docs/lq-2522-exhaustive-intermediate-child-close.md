# LQ-2522 Exhaustive intermediate child close

- Every successfully opened child descriptor is recorded by fixed child name.
- Finalization attempts to close every recorded child exactly once.
- One failing close does not short-circuit remaining child cleanup.
- Child cleanup occurs on success, controlled rejection, and system failure paths.
- No child descriptor is intentionally transferred beyond the verifier.
- Cleanup order remains bounded by at most four fixed phase outputs.
