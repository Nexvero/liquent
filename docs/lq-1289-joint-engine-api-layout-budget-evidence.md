# LQ-1289 Joint engine API layout budget evidence

- Parameterized tests exercise all ten-, eleven-, and fourteen-source roots.
- Every generation succeeds at its exact observed cumulative size.
- Every generation rejects when that budget is reduced by one byte.
- Every generation proves the same deterministic early cutoff behavior.
- Existing fixtures retain canonical private files and directory modes.
- Stable source and root mutation tests remain green beside this evidence.
- Architecture guardrails remain part of focused verification.
