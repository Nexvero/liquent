# LQ-2584 Single new-output capture call

- The phase loop retains one child-identity helper call in source.
- That call is reached only for a phase with one fixed mapped output name.
- It captures a newly created directory before adding it to expected state.
- Existing retained identities are never recaptured or silently refreshed.
- Duplicate mapped-name capture remains a controlled rejection.
- Caller-supplied names never reach this operation.
