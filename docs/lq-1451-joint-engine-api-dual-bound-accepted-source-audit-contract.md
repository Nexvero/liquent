# LQ-1451 Joint engine API dual-bound accepted-source audit contract

- Accepted-source audit may receive source and acceptance identities.
- Source identity constrains both source snapshot observations.
- Acceptance identity constrains both marker observations.
- Neither root may be replaced between outer resolution and audit.
- The two identities remain independent mandatory facts.
- Failure stays fail-closed and detail-free at the existing boundary.
- Unbound direct audit use remains supported.
