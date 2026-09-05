# LQ-1510 Joint engine API source observation audit

- LQ-1507 through LQ-1509 close descriptor source observation.
- Snapshot equality now has corresponding filesystem-state evidence.
- Root and every fixed-layout child contribute immutable state.
- Existing loader callers continue receiving only the snapshot.
- Failure remains fail-closed and detail-free.
- No schema, CLI, or persistence decision was introduced.
- Cross-decision continuity remains the next boundary.
