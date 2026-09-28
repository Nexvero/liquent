# LQ-1920 Joint engine API validated audit marker reads

- Accepted audit performs two outer target-marker reads.
- First follows closed result construction.
- Terminal read follows final source freshness verification.
- Both must equal retained result marker evidence.
- Registry audit performs no target-marker read.
- Audit mode binding governs marker access.
- Existing verifier-internal reads remain unchanged.
