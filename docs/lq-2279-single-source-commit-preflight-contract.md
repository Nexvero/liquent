# LQ-2279 single-source-commit preflight contract

- One controlled preflight run is bound to exactly one source commit.
- The first clean 40-character commit identity becomes the run identity.
- Every later phase must observe that same clean commit again.
- A different clean commit is not an equivalent continuation.
- Working-tree cleanliness remains rechecked independently each phase.
- The commit fact grants no build, signing, or publication authority.
- Cross-run persistence and release registration remain separate.
