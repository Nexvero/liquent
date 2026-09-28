# LQ-1696 Composed joint engine API terminal gate

- Success check owns terminal observation and timing.
- Wrapper still owns exact final root validation.
- Audit-only paths remain unchanged.
- Public accept-once returns no new value.
- Existing CLI arguments and exit codes remain stable.
- Failure revalidation remains branch-compatible.
- No external interface is added.
