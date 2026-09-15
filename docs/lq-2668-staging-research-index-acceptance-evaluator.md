# LQ-2668 – Staging Research-index acceptance evaluator

## Result

LQ-2668 implements the closed application evaluator required by LQ-2667.

It evaluates sanitized observations already acquired for one bound execution.
It performs no network access, persistence, file access, repair, mutation,
deployment, rollback, or promotion.

## Bound run

Each run requires a canonical lowercase SHA-256 candidate digest, exact HTTPS
staging origin, and aware UTC observation time.

Origins with credentials, paths, queries, fragments, plaintext HTTP, or no
host are rejected before evaluation. Mutable tags cannot stand in for the
candidate digest.

## Closed observation vocabulary

The evaluator accepts exactly one observation for each required contract
check: anonymous closure, authorized empty page, authorized visible page,
minimum fields, security headers, query rejection, fresh revocation, and
detail-free unavailability.

Each observation is classified only as passed, failed, or unavailable. It
carries no body, cookie, token, identity, workspace, JobId, provider detail,
diagnostic text, or mutation handle.

## Evaluation

A complete once-only set of passed observations returns accepted.

Any failed observation returns rejected. Any unavailable observation in an
otherwise structurally complete set returns unavailable.

Missing, duplicate, replaced, or otherwise non-canonical observation sets
return rejected before individual outcomes can establish acceptance.

The result retains only the bound run and overall classification. It grants no
authority and triggers no follow-up operation.

## Verification

Tests prove all-pass acceptance, independent failure of every mandatory check,
unavailability separation, closed-set cardinality, duplicate rejection, and
strict digest, origin, and UTC validation.

## Explicit non-goals

This slice adds no HTTP client, request construction, redirect handling,
authentication material, CLI, evidence serialization, file output, workflow,
runbook, release action, deployment, promotion, rollback, or live staging use.

It changes no application or edge route, schema, SQL, migration, container,
secret, DNS, TLS, OIDC, identity, membership, permission, session, or Research
job fact.

## Next step

A later operator slice may acquire already authorized observations and pass
only their sanitized classifications into this evaluator. Credential handling,
authority mutation, and promotion remain outside that read-only operator.
