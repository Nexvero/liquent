# LQ-2581 Single intermediate verification-authority contract

- One complete verifier decides retained intermediate state before each phase.
- One complete verifier decides resulting intermediate state after each phase.
- Separate path-stat loops no longer duplicate either security decision.
- The verifier already binds topology, descriptors, identities, and metadata.
- New mapped output capture remains a distinct identity-creation operation.
- Verification authority grants no publication or deployment authority.
