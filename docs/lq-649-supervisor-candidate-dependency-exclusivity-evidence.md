# LQ-649 — Supervisor candidate dependency exclusivity evidence

## Status

Implemented as executable inert-construction and source-graph evidence.

## Evidence

Sentinel dependencies raise on every attribute access. Candidate construction
succeeds without touching them, proving it is inert. The result contains exactly
candidate Prepare, observation-only Release, one-shot child, and read-only
reconciliation components.

AST evidence finds exactly one `executor=` keyword and proves its value is
`child_capability_executor`. The parent Release construction contains its token
publisher and no executor. Compatibility Prepare, Release, aggregate service,
and old composition names are absent.

The immutable bundle rejects mutation or constructor override of Terminal and
Production claims. Incomplete dependencies fail before I/O through the existing
detail-free boundary. No settings, app factory, CLI, actor authority, Docker, or
SQL dependency is present.

LQ-650 records the candidate readiness decision and next blocker.
