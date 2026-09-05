# LQ-1627 Joint engine API success state handoff contract

- Successful acceptance captures its final directory state.
- The captured state precedes outer validation.
- Outer validation must compare that exact state.
- A newer state may not be adopted implicitly.
- Root and source state remain unchanged.
- Failure paths retain fail-closed revalidation.
- No caller state is accepted.
