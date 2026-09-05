# LQ-1442 Joint engine API one-shot source identity audit

- LQ-1439 through LQ-1441 close one-shot source identity propagation.
- Both source observations share one externally resolved identity fact.
- Source and acceptance bindings remain separate and jointly required.
- Replacement cannot become the verification basis after resolution.
- Existing fail-closed and detail-free behavior is preserved.
- No new CLI, storage, schema, or runtime ownership decision was made.
- Operation-root propagation remains the final boundary in this strand.
