# LQ-1692 Terminal monotonic joint engine API gate

- Existing trusted monotonic helper is reused.
- A third outer monotonic read closes live finalization.
- Completion and terminal ordering is explicit.
- Initial-to-terminal duration is checked independently.
- Exactly 30 seconds remains accepted.
- No policy setting or CLI option changes.
- Technical clock failure remains detail-free.
