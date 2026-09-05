# LQ-2421 Cross-gate distribution-directory identity

- Every distribution-pair revalidation requires the retained parent identity.
- Wheel and sdist must share that same private parent directory.
- Each later wheel, entry-point, sdist, and bundle use therefore rechecks custody.
- Terminal inventory accepts and verifies the retained directory identity explicitly.
- Byte-identical artifacts in a newly created same-named directory are rejected.
- Candidate creation follows both parent continuity and exact two-file inventory.
