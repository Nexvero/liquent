# LQ-1704 Root-bound joint engine API audit success check

- Success check receives the second resolved root snapshot.
- Registry mode rereads both retained inventories.
- Accepted-source mode rereads source and marker observations.
- Every reread uses second-snapshot identities.
- Exact equality is required before final validation.
- No write or retry occurs.
- Technical failure remains detail-free.
