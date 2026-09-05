# LQ-1356 Final joint engine API operation child metadata gate

- Initial child states are captured after initial identity resolution.
- Final child states are captured after final root-chain validation.
- Ordered initial and final state tuples must match exactly.
- The comparison covers both canonical child positions.
- Final private-directory checks run before state values are returned.
- Any observation failure closes its locally owned descriptor.
- The shared root validator owns the final comparison.
