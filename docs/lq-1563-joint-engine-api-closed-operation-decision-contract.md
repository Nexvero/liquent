# LQ-1563 Joint engine API closed operation decision contract

- Accept and audit consume only closed operation-root values.
- Child topology validation precedes inner decision invocation.
- Invalid paths or identities cannot reach source or registry readers.
- Final topology validation follows success and failure.
- Caller roles and allow flags remain irrelevant.
- No fallback topology is accepted.
- Technical details remain internal.
