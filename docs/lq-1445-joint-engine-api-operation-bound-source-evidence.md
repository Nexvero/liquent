# LQ-1445 Joint engine API operation-bound source evidence

- Tests capture both child identities passed by operation acceptance.
- A same-content source swap before inner verification is rejected.
- The acceptance registry remains empty after that rejection.
- Exact identity binding succeeds through the established path.
- Prior operation and marker revalidation suites remain green.
- Strict warning treatment guards compatibility regressions.
- External image and staging evidence remains separately required.
