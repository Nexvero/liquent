# LQ-1540 Closed source observations in accept and audit

- Existing observation capture constructs the closed value directly.
- One-shot and accepted audit require exact observation types.
- Root and child semantics are checked on every capture.
- Cross-observation equality follows successful construction.
- Marker and registry checks remain unchanged.
- Operation-root validation remains an outer defense.
- Public command surfaces do not expand.
