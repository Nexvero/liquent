# LQ-1432 Joint engine API operation bound write

- Operation-root resolution captures root and both child identities.
- Accept mode passes the acceptance identity into one-shot verification.
- One-shot forwards it into durable marker record.
- Record compares it with the descriptor opened for the actual write.
- Any mismatch rejects before marker creation.
- Shared finally-based operation finalization still runs after rejection.
- Existing command parser and mode surface remain unchanged.
