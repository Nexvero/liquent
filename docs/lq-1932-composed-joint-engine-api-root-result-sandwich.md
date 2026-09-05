# LQ-1932 Composed joint engine API root result sandwich

- Validated initial roots open the operation sandwich.
- Operation runs only against those exact roots.
- Validated current roots precede success finalization.
- Existing final root validation closes the sandwich.
- Mutation and read-only modes retain distinct rules.
- Every stage rejects malformed root result directly.
- No additional filesystem authority is introduced.
