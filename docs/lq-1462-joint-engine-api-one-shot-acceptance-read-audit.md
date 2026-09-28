# LQ-1462 Joint engine API one-shot acceptance read audit

- LQ-1459 through LQ-1461 close one-shot marker-read binding.
- Both marker observations share one externally resolved identity.
- Path continuity and identical bytes cannot replace root identity.
- Source and acceptance identities remain separate facts.
- Existing fail-closed detail-free behavior is preserved.
- No new schema, storage, CLI, or exception decision was made.
- Phase-specific replacement remains the next evidence boundary.
