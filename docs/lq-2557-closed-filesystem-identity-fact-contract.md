# LQ-2557 Closed filesystem-identity fact contract

- Workspace and child identities are validated before filesystem observation.
- Each identity is exactly one two-item tuple of nonnegative integers.
- Boolean, string, negative, short, long, and container substitutes fail closed.
- Validation applies to the local expected-identity snapshot.
- Invalid facts never reach path opening, listing, or metadata comparison.
- Identity validity grants no publication, deployment, or release authority.
