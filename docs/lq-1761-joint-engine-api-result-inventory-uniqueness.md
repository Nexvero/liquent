# LQ-1761 Joint engine API result inventory uniqueness

- A result cannot repeat an accepted run identity.
- A result cannot repeat a marker filesystem identity.
- A result cannot repeat a complete marker state.
- The three checks protect distinct observable facts.
- Equality shortcuts cannot disguise duplicated evidence.
- Violations fail before operation success is finalized.
- No new persistence constraint is introduced.
