# LQ-2601 Clean-tree controlled-preflight completion evidence

- The controlled local preflight passed against code commit `d273c9af6b8cb5ad62fed399821b5570beef906b`.
- Its source gate observed an exact commit and completely clean Git tree.
- Runtime, source, normal tests, PostgreSQL tests, distributions, wheel, entrypoints, sdist, final diff, and bundle all passed.
- The run used Python 3.12.14 and the exact `requirements/ci.lock` tool versions.
- PostgreSQL 16.14 was reached through the required explicit test DSN with UTC sessions.
- Evidence was atomically published below a private owner-only local directory.
- The canonical receipt binds all ten ordered phase digests to the same source commit.
- The receipt explicitly leaves publishing and deployment authorization false.
- No external signature, registry mutation, upload, staging action, or deployment occurred.
