# LQ-2660 – Workspace Research-read destination

## Result

LQ-2660 adds the first static read-only Research destination for an
authenticated actor with current Research-read authority in one current
workspace.

The destination is the fixed path `GET /research`. The authorized landing from
LQ-2659 links only to that path and does not carry a workspace, role,
permission, capability, or allow value.

## Request boundary

The route accepts only an exact query-free `GET`. Query-bearing requests are
rejected empty with `400`, and every other method is rejected empty with `405`
and `Allow: GET`.

Input rejection occurs before session, workspace, or membership lookup. The
browser cannot select or suggest a target workspace through the URL, request
body, header, cookie, or form field.

The route exists only when session, current-workspace, and Research-membership
dependencies are completely composed. It does not create a permissive fallback
for an incomplete application.

## Authority sequence

The existing browser-session lookup first resolves the current active session.
The resulting `SessionPrincipal` identifies only the actor and supplies no
operation authority.

The LQ-2658 application decision then resolves one current workspace context
from the system of record for that actor. No context or an ambiguous context
stops before Research-membership lookup.

For one context, the decision freshly resolves the membership for the exact
actor and workspace and requires `research:read`. The established
`research:write`-implies-read policy remains unchanged; read never implies
write.

No caller-supplied boolean, role, status, capability, permission snapshot, or
WorkspaceId participates in the decision.

## Observable outcomes

An allowed request returns a static HTML document stating only that read-only
Research access is available. It contains a fixed return link to `/`.

The document exposes no internal user or workspace identifier, membership
state, permission set, role, capability, job, artifact, provider value,
session value, or CSRF material. It contains no script or form.

The success response uses `no-store` and `no-referrer` so the authorization
result is not treated as reusable browser state.

Missing or invalid authentication retains the established neutral redirect to
`/login`. A malformed or stale supplied session cookie is cleared by that
existing boundary.

Missing or ambiguous workspace context and every Research authorization denial
share the same empty `404` response. The result does not distinguish absence,
inactivity, missing permission, revocation, or actor/workspace mismatch.

Session, workspace-context, or membership-store failure uses the existing
detail-free redirect to `/login/unavailable`. Technical unavailability is not
disguised as absence or denial and does not clear a potentially valid session.

## Freshness and revocation

Every request resolves the browser session, workspace context, and Research
membership again from their current sources of record.

No successful landing request, link visibility, route response, browser value,
process object, or adapter cache can authorize a later request.

A committed session revocation, identity or workspace deactivation,
membership deactivation, or Research-permission removal therefore affects the
next request.

## Authority separation

The route grants no Research write, job creation, job cancellation, artifact
publication, onboarding management, membership management, role management,
workspace lifecycle, or user lifecycle authority.

Ordinary membership remains distinct from Research permissions, and all
management capabilities remain distinct from both. Visibility of the link or
document is never accepted by another operation as proof of authority.

Every later resource-bearing operation must bind the actor, workspace,
resource, and required operation afresh from the system of record.

## Verification

Tests prove explicit read authority, the existing write-implies-read rule,
detail-free content, exact actor/workspace lookup, neutral absence and denial,
early stop without context, technical-unavailability separation, rejection
before lookup, and the fixed authorized link.

The LQ-2658 and LQ-2659 regression boundaries remain in the focused suite.

## Explicit non-goals

This slice adds no job list, job detail, evidence view, job start, write
operation, workspace selector, dynamic navigation, API payload, or client-side
application.

It creates or mutates no user, workspace, admission, external-identity binding,
session, membership, role, capability, permission, authority, Research job, or
artifact.

It adds no schema, table, migration, SQL statement, port, persistence model,
CLI, operator command, bootstrap behavior, edge rule, deployment wiring, or
staging mutation.

## Next step

A later slice may expose the exact `/research` path at the staging edge and
perform real acceptance. A persistent authorized job index remains a separate
contract and implementation decision.
