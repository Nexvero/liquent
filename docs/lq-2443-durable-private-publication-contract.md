# LQ-2443 Durable private-publication contract

- Relative rename alone is insufficient for durable local namespace publication.
- The already bound private parent directory must be synchronized after rename.
- Synchronization failure remains inside the identity-bound rollback boundary.
- Success also requires terminal parent, source-name, and output-name verification.
- No file copy, overwrite, alternate parent, or destructive fallback is allowed.
- Durability of local evidence does not authorize deployment or external publication.
