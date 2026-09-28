# LQ-1391 Joint engine API acceptance root mutation contract

- Any root metadata mutation during read-only work invalidates the result.
- Restoring mode to private does not erase the changed ctime fact.
- Touching the registry root invalidates timestamp continuity.
- Mutation rejection applies equally to marker load and full inspection.
- No retry or new-baseline fallback follows detected mutation.
- Marker validity cannot compensate for unstable root state.
- Rejection occurs before a read-only result becomes observable.
