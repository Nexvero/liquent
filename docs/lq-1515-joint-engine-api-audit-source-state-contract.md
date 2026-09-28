# LQ-1515 Joint engine API audit source state contract

- Accepted-source audit must retain one complete source observation.
- Final observation must match all initial source facts.
- Same-inode rewrite with restored bytes invalidates the audit.
- Marker and acceptance-root observations remain independent.
- Temporal and cryptographic verification remains mandatory.
- Failure stays detail-free and read-only.
- Operation-root validation remains an outer defense.
