# LQ-1619 Joint engine API created generation delta contract

- Registry delta addition must equal one-shot result exactly.
- Acceptance equality alone is insufficient.
- Marker identity and complete state must also match.
- Existing marker observations remain preserved.
- Source-derived expected acceptance remains independently checked.
- No caller-supplied generation is accepted.
- Mismatch fails detail-free.
