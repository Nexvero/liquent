# LQ-1559 Joint engine API operation identity distinctness contract

- Operation root, source root, and acceptance root are distinct facts.
- No child identity may equal the operation-root identity.
- Source and acceptance identities may not alias each other.
- Each identity remains an exact nonnegative device-inode pair.
- Identity collision invalidates the topology.
- No caller allow decision can override collision.
- Failure reveals no identity values.
