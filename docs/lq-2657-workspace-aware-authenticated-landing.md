# LQ-2657 – Workspace-aware authenticated landing

## Result

LQ-2657 composes the LQ-2656 current-workspace resolver into the authenticated
landing from LQ-2653. A database-backed application automatically uses the
persistent resolver; explicit test composition remains possible.

The route remains `GET /`. No new public path, edge rule, schema, migration,
or mutation is added.

## Session before workspace

The route first resolves the current browser session through the established
session system of record. Missing, malformed, unknown, expired, or revoked
sessions retain the neutral redirect to `/login` and existing cookie clearing.

Only the `UserId` inside the successfully resolved `SessionPrincipal` is passed
to the workspace-context lookup. The session supplies no WorkspaceId,
membership, role, capability, permission, or allow decision.

Rejected methods and query-bearing requests still stop before both session and
workspace lookup. A caller cannot select a workspace through the URL.

## Workspace-aware documents

Exactly one current active workspace context produces a static statement that
the actor's workspace context is available.

Neutral absence produces one static statement that no workspace context is
available. It does not distinguish zero memberships, multiple memberships,
inactive facts, or an unknown relationship.

Neither document includes internal user or workspace identifiers, candidate
counts, provider data, membership state, permission names, capabilities,
session values, or CSRF material.

Both documents retain `no-store` and `no-referrer`. They contain no script,
form, workspace selector, or operation link.

## Authority boundary

The visible workspace context is not operation authority. It does not grant or
imply research read, research write, onboarding management, membership
management, lifecycle management, or any future permission.

Every later operation must resolve its own target and current authorization
from the system of record. The landing result must never be reused as an allow
decision.

## Composition

When `create_app` owns or receives a database engine and no explicit landing
context lookup was supplied, it creates `DatabaseCurrentWorkspaceContexts`
against that same engine.

An explicitly supplied lookup retains precedence for isolated tests and
controlled composition. No lookup occurs during app construction.

Without a database or explicit workspace resolver, the established LQ-2653
session-only document remains unchanged. The default app still exposes no
landing route without complete OIDC callback composition.

## Revocation and unavailability

Each landing request performs current session resolution followed by current
workspace resolution. Committed user, workspace, membership, or session
deactivation therefore affects the next request without a cache.

Workspace persistence failure uses the existing detail-free redirect to
`/login/unavailable`. It is not presented as neutral absence and does not clear
a potentially valid session cookie.

No new public exception, error code, or diagnostic surface is introduced.

## Verification

Tests cover a unique workspace, neutral absence, technical unavailability,
query rejection before workspace lookup, and automatic database composition.

Existing authenticated-landing and persistent workspace resolver tests remain
unchanged and green.

## Explicit non-goals

This slice creates or mutates no user, workspace, admission, identity binding,
membership, role, capability, permission, authority, or browser session.

It adds no workspace chooser, navigation, research UI, management UI, API
payload, edge exposure, CLI, operator command, bootstrap, schema, or migration.

Real staging acceptance and any product operation linked from this landing
remain separate later slices.
