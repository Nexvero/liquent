# LQ-1815 Joint engine API accepted evidence failure contract

- Every malformed evidence shape uses one boundary failure.
- Failure text contains no source or marker detail.
- Underlying container behavior is not disclosed.
- Root validation remains guaranteed through finalization.
- Direct operation callers receive the same closed failure.
- CLI still maps all failures to its existing status.
- No new exception name is introduced.
