# LQ-1672 Composed joint engine API operation time check

- Existing trusted clock helpers are reused.
- Outer wall reads share the one-shot clock boundary.
- Monotonic reads use the established bounded helper.
- No CLI clock or duration option is added.
- Audit-only modes retain existing timing behavior.
- Accept-once public result and exit codes remain unchanged.
- Technical clock failures remain detail-free.
