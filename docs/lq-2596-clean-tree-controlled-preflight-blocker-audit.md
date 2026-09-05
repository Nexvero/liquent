# LQ-2596 Clean-tree controlled-preflight blocker audit

- PostgreSQL required tests, local image build, smoke, and Grype now pass.
- The real controlled local runner still rejects before publishing evidence.
- Its source gate requires an exact commit and completely clean Git tree.
- The current cumulative work intentionally remains uncommitted and unstaged.
- The fixed public error does not disclose or guess an internal phase name.
- No output target or matching temporary workspace remained after rejection.
- Passing the runner now requires authorized branch, review, staging, and commit.
- A commit must represent the reviewed cumulative state, not hide dirty input.
- External signing and staging acceptance remain subsequent independent gates.
- Production readiness and deployment authority remain false.
