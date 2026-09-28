# LQ-2285 cross-phase source-bound pair gate

- Pair capture requires an established commit and source epoch.
- Every later pair check requires both provenance facts again.
- The check recomputes one identity from current files and bound source state.
- Current version, digests, provenance, and pair digest must all agree.
- Missing provenance is neutral unusability and rejects fail closed.
- Caller-provided source claims cannot override the bound run state.
- Rejection remains detail-limited and performs no mutation.
