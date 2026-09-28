# LQ-2004 Composed joint engine API clock failure policy

- Accept inherits normalized UTC and monotonic reads.
- Registry-Audit inherits normalized monotonic reads.
- Accepted-Audit inherits both clock gates.
- Initial failures prevent entered operation work.
- Late failures preserve durable acceptance.
- Root closure remains authoritative.
- CLI status policy remains unchanged.
