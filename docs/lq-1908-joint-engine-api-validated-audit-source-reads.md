# LQ-1908 Joint engine API validated audit source reads

- Accepted audit uses two outer validated source reads.
- First follows closed result construction.
- Terminal read follows final freshness verification.
- Both must equal retained result source evidence.
- Registry audit performs no source observation.
- Audit mode binding governs source access.
- Existing verifier-internal reads remain unchanged.
