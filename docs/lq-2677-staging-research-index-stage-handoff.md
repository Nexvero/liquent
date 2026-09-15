# LQ-2677 – Staging Research-index stage handoff

## Result

LQ-2677 binds independently acquired baseline, after-revocation, and
unavailability classifications to one validated acceptance run.

Only an exact three-stage set sharing the same candidate digest, HTTPS origin,
and UTC execution binding can reach reduction and evaluation.

## Closed handoff

Each handoff validates the exact check and phase inventory for its stage.
Missing, duplicate, unknown, or incorrectly phased classifications are rejected
when the handoff is created.

Final evaluation requires each stage exactly once. Caller ordering has no
authority; stages are restored to their canonical order internally. Mixed run
bindings are rejected before reduction.

The handoff contains only the established run, stage, and sanitized
classifications. It carries no response, credential, identity, workspace,
JobId, mutation handle, provider text, or diagnostic detail.

## Revocation boundary

Binding before- and after-revocation classifications to one run does not prove
who performed the intervening mutation and grants no ability to perform or
restore it. Mutation authorization remains external and explicit.

## Verification

Tests prove exact same-run acceptance, order independence, mixed-run rejection,
complete stage and phase inventories, duplicate rejection, and preservation of
technical unavailability.

## Explicit non-goals

This slice adds no HTTP acquisition, credential loading, revocation or restore,
clock, persistence, evidence file, CLI, workflow, deployment, promotion,
rollback, schema, migration, route, image, secret, or installed operator.

## Next step

A later evidence codec may serialize only the bound sanitized classifications
or final result under owner-private file controls. Real staging execution,
mutation coordination, and promotion remain separate.
