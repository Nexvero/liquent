# LQ-1943 Mutation-aware joint engine API root completion

- Failed accept may allow only acceptance-state change.
- That path forwards explicit true allowance.
- Successful accept validates captured expected final state.
- Both paths require exact none validator completion.
- Foreign completion never erases durable marker state.
- No cleanup or retry is introduced.
- Mutation semantics remain unchanged.
