# LQ-2561 Invalid-identity no-I/O rejection

- Rejection of invalid identity facts is independent of filesystem state.
- Evidence replaces workspace opening with a test that must remain unreachable.
- Invalid workspace and child facts both stop before that boundary.
- The result is the existing controlled preflight rejection only.
- No descriptor therefore exists or requires cleanup on this path.
- No retry, fallback lookup, or identity regeneration occurs.
