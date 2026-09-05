# LQ-2170 Reproducible sdist evidence

- Distinct input mtimes produce byte-identical normalized archives.
- Focused tests cover payload, ordering, ownership, and epoch facts.
- Invalid SOURCE_DATE_EPOCH values are rejected before replacement.
- Composition records the hash only after normalization.
- Existing sdist structural checks remain mandatory.
- No publish, signing, container, or deployment step is added.
- Production readiness still requires external release evidence.
