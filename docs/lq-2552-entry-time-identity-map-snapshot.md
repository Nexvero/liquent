# LQ-2552 Entry-time identity-map snapshot

- The verifier copies the complete supplied mapping at function entry.
- Keys and device/inode tuples retain their exact Python values.
- No lazy mapping lookup occurs after filesystem checks begin.
- The original mapping remains externally owned and is never modified here.
- Empty expected state becomes one explicit empty local dictionary.
- Snapshot creation performs no filesystem or callback operation.
