# LQ-1883 Joint engine API validated accept registry reads

- Accept baseline uses the shared validated reader.
- Post-mutation inventory uses the same reader.
- First success recheck uses the same reader.
- Terminal inventory recheck uses the same reader.
- All four reads share one root identity and invariants.
- Malformed evidence fails at its immediate boundary.
- Mutation semantics remain unchanged.
