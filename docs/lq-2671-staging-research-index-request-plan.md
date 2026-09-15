# LQ-2671 – Staging Research-index request plan

## Result

LQ-2671 implements the pure closed request plan anticipated by LQ-2670.

The plan derives fixed `GET` requests from a validated acceptance run. It
performs no network access, credential loading, classification, persistence,
mutation, deployment, or promotion.

## Closed plan

The plan contains nine ordered requests covering the eight LQ-2668 checks.
Revocation freshness has distinct before- and after-revocation phases; every
other check has one request. Every URL is derived from the validated HTTPS
origin and exact `/research` path.

Anonymous closure and query rejection use no credential slot. Authorized,
revocation-fixture, and unavailable-fixture observations name distinct opaque
credential slots without containing credential values.

The query rejection request uses one fixed sentinel query. No caller input can
select a workspace, page size, role, permission, URL, method, or allow result.

## Safety boundary

A credential slot is routing metadata, not authentication material or
authority. The deployed system must still resolve actor, workspace, membership,
and Research permission freshly from its system of record.

The plan carries no headers, cookies, tokens, bodies, identities, WorkspaceIds,
JobIds, roles, allow booleans, timeouts, retries, redirects, or mutation handles.

## Verification

Tests prove exact check coverage and order, the mandatory revocation pair,
exact method and URL derivation, credential-free anonymous requests, closed
fields, and rejection of unbound input.

## Explicit non-goals

This slice adds no HTTP client, response classifier, credential store, CLI,
file format, evidence writer, workflow, release action, deployment, promotion,
rollback, schema, migration, route, image, or live staging call.

## Next step

A later slice may classify bounded response summaries for this closed plan.
Transport execution, secrets, revocation mutation, final evidence, and
promotion remain separate.
