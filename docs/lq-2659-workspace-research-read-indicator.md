# LQ-2659 – Workspace Research-read indicator

## Result

LQ-2659 adds a detail-free Research-read availability indicator to the existing
workspace-aware authenticated landing.

The indicator appears only when the current session actor has a unique current
workspace context and a fresh Research-read authorization for that same
workspace. No new route, resource list, or operation is exposed.

## Decision sequence

`GET /` continues to resolve the active browser session first and the current
workspace context second. Only the internal `UserId` from the resolved
`SessionPrincipal` enters these lookups.

After one workspace context is available, the landing applies the LQ-2658
Research-read decision to that already resolved context. The context actor must
equal the session actor before the membership lookup occurs.

The existing authorization boundary then resolves the current membership for
the exact actor and workspace and evaluates `research:read`. The established
`research:write`-implies-read rule remains unchanged.

No caller-supplied workspace, role, status, capability, permission, or allow
boolean participates in the decision. Rejected methods and query-bearing
requests stop before all authority lookups.

## Observable result

An allowed decision adds only the static statement `Research read access is
available.` to the existing workspace-context document.

The document contains no user or workspace identifier, membership state,
permission set, role, capability, provider data, session value, or CSRF
material. It remains script-free and retains `no-store` and `no-referrer`.

A missing or inactive membership, absent Research permission, or other policy
denial preserves the ordinary workspace-context document without the
indicator. No denial reason is exposed.

An absent or ambiguous workspace context preserves the existing neutral
no-context document and stops before Research membership resolution.

## Technical unavailability

Workspace-context and Research-membership persistence failures use the existing
detail-free redirect to `/login/unavailable`.

Technical unavailability is not rendered as absence or authorization denial.
It does not clear a potentially valid browser-session cookie and introduces no
new exception or public error shape.

## Freshness and revocation

Every landing request resolves the session, workspace context, and Research
membership from their current sources of record. The landing stores no allow
decision in a session, browser, route, process, or adapter cache.

A committed session, user, workspace, or membership deactivation and a
committed Research-permission revocation therefore affect the next request.

The visible indicator is informational output from that request only. It is
not a reusable authority token, and every future destination must independently
authorize its own actor, workspace, resource, and operation.

## Authority separation

An authenticated `SessionPrincipal` continues to identify only the actor.
Authentication alone does not make the indicator visible and grants no
Research or management authority.

Ordinary membership and workspace visibility also remain insufficient. The
indicator requires the separate explicit Research permission.

Research-read authority does not imply Research write, onboarding management,
membership management, role management, lifecycle management, or any other
administrative capability.

## Composition

Database-backed applications already compose the current-workspace resolver
and Research-membership lookup against the application engine. The landing
reuses those current dependencies without introducing another port or adapter.

Explicit dependency injection remains available for isolated tests. If no
Research-membership dependency exists, the previous workspace-aware document
is preserved without an indicator.

## Verification

Tests prove visibility for explicit read and write-implies-read authority,
neutral omission for missing, inactive, and permissionless memberships, early
stop without a workspace context, actor binding, rejection before lookup, and
the established detail-free technical-unavailability redirect.

Existing workspace-context, authenticated-landing, and LQ-2658 authorization
tests remain part of the regression boundary.

## Explicit non-goals

This slice adds no Research destination, hyperlink, navigation menu, job list,
job detail, job start, workspace chooser, API payload, or edge rule.

It creates or mutates no user, workspace, admission, external-identity binding,
session, membership, role, capability, permission, authority, or Research job.

It adds no schema, table, migration, SQL statement, port, persistence model,
CLI, operator command, bootstrap behavior, or deployment wiring.

## Next step

A later slice may introduce a read-only Research destination behind its own
fresh, target-bound authorization. Edge exposure and real staging acceptance
remain separate decisions.
