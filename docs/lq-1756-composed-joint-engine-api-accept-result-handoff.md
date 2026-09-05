# LQ-1756 Composed joint engine API accept result handoff

- Existing source observation is reused without copying.
- Existing registry observation tuple is reused exactly.
- No additional read is needed for result construction.
- Existing success-check ordering remains unchanged.
- Existing public CLI and exit behavior remain stable.
- Failure revalidation remains branch-compatible.
- No external result interface is introduced.
