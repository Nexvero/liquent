# LQ-1418 Joint engine API pre-create rebinding audit

- Pre-create path mutation has no durable or transient marker side effect.
- The gate closes the gap between initial root open and file creation.
- Post-write rebinding remains an explicit unknown-outcome failure window.
- Tests distinguish pre-create and post-write mutation timing.
- Existing durable-marker preservation semantics remain unchanged.
- Focused timing and compatibility evidence passes.
- No broader rollback or deletion capability is introduced.
