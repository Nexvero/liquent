# LQ-2655 – Workspace-aware read surface contract

## Status

This slice defines the next browser-facing contract after the authenticated
landing acceptance. It makes no route, persistence, schema, migration, port,
model, composition, edge, or deployment change.

## Context

LQ-2653 proves that a current browser session can terminate safely at `/`.
LQ-2654 records the real staging acceptance of that journey. The resulting
document deliberately identifies no workspace and grants no authority.

The next product step needs a workspace-aware read surface without turning a
session, a caller-selected identifier, or ordinary membership into ambient
authority. Existing persistent membership and research capability facts remain
the system of record.

## Observable surface

An implementation may expose one authenticated, read-only browser surface for
the actor's current workspace context.

The surface must be reached only after resolving the current browser session.
The resulting `SessionPrincipal` identifies the actor and nothing more.

The response may confirm that one workspace context is available and may offer
navigation to separately authorized read functions. It must not expose the
internal `UserId`, `WorkspaceId`, external provider subject, session identifier,
CSRF material, admission record, authority revision, role, or capability set.

The response must be static or server-rendered, cache-disabled, and protected
by the established no-referrer and browser security policy.

## Authoritative workspace resolution

The target workspace must be resolved server-side from current persistent
facts for the authenticated actor.

No query value, form value, path component, header, cookie, redirect target,
provider claim, or session payload may select or assert a workspace.

The resolver must bind all of the following from the same system of record:

- the stable internal actor identity;
- the active lifecycle state of that user;
- the stable internal workspace identity;
- the active lifecycle state of that workspace;
- the actor's current active ordinary membership in that workspace.

The resolver must not accept a caller-supplied allow boolean, role, membership
status, permission collection, or preconstructed authority result.

If the product later supports more than one active workspace membership, the
selection rule requires a separate explicit contract. This slice must not pick
the first row, rely on database ordering, infer recency, or silently choose a
workspace.

## Membership and capability boundary

Ordinary active membership is required only to establish that the workspace
context is visible to the actor. It does not authorize research reads, research
writes, onboarding management, membership management, lifecycle management, or
any other operation.

Every linked function must perform its own current authorization decision.
For research data, the existing explicit `research:read` or implied read from
`research:write` policy remains authoritative.

Onboarding-management and membership-management capabilities remain separate
from ordinary membership and research permissions. Their presence must not be
displayed or inferred by this surface.

The surface itself performs no mutation and offers no mutation endpoint.

## Active and inactive facts

Users, workspaces, and memberships are active only when the persistent value is
exactly the established active state.

Unknown, missing, inactive, malformed, contradictory, or otherwise
unreconstructable authority facts must fail closed. No historical membership,
session age, provider success, bootstrap origin, or previous response may
override the current decision.

Each later request must resolve current facts again. A committed user,
workspace, or membership deactivation must therefore affect the next decision.
No browser, route, process, or session cache may preserve workspace visibility.

## Neutral absence and rejection

No current eligible workspace context produces one neutral outcome. The
browser must not be able to distinguish an unknown user, inactive user,
unknown workspace, inactive workspace, absent membership, inactive membership,
ambiguous multiple memberships, or a context that is no longer visible.

The outcome must reveal no identifier, count, status, prior association, or
reason. It must not claim that a workspace can be created or requested.

Missing, malformed, expired, revoked, or unknown sessions continue to use the
existing neutral authentication outcome and cookie handling from LQ-2653.

Input outside the exact future surface contract must be rejected before any
session or workspace lookup and without reflection.

## Technical unavailability

If the current session or workspace-context system of record cannot provide a
decision, the response must use the existing detail-free technical-
unavailability presentation.

Technical unavailability is not neutral absence, authentication failure, or an
authorization denial. It must not clear a potentially valid session or cache a
negative workspace decision.

No new public exception or error name is defined here. SQL, table, constraint,
driver, host, port, DSN, user, workspace, membership, and permission details
remain undisclosed.

## Retention and non-reuse

Stable internal `UserId` and `WorkspaceId` values remain non-reassignable.
Deactivation must not make either identifier available to another subject or
workspace.

The system must retain enough durable identity, workspace, membership, and
lifecycle history to prevent reuse and to interpret later revocation safely.
This is a lower bound, not a schema, retention-period, archival, or deletion
design.

## Explicit non-goals

This slice creates no user, workspace, admission, identity binding, membership,
role, capability, permission, session, or authority fact.

It defines no workspace chooser, invitation, onboarding flow, profile page,
research result page, write control, administration UI, operator command, API
payload, URL, HTTP status, template, or visual design.

It makes no schema, table, SQL, migration, port, model, signature, test, CLI,
wiring, edge, secret, deployment, release, or bootstrap decision.

Initial bootstrap remains complete and separate. Regular membership and
capability persistence already provide current authority facts; their future
product-facing mutation and lifecycle controls remain separate work.

## Implementation checkpoint

A later implementation slice must first define a narrow read-only resolver for
the actor's current workspace context and prove deterministic fail-closed
handling of zero, one, and multiple eligible memberships.

Only after that resolver is independently tested may a browser route compose
it with the current session lookup. Edge exposure, product navigation, real
staging acceptance, and any workspace selection mechanism remain later slices.
