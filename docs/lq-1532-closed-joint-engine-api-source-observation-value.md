# LQ-1532 Closed joint engine API source observation value

- Immutable construction validates shape and filesystem semantics.
- Root type, owner, and exact mode are mandatory.
- Child type, owner, mode, link count, and size are mandatory.
- Limits follow the fourteen fixed-layout source positions.
- Boolean and malformed integer state remains rejected.
- Redacted representation remains unchanged.
- No serialized or persistent form is introduced.
