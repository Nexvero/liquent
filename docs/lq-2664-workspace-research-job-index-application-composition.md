# LQ-2664 – Workspace Research-job index application composition

## Result

LQ-2664 composes the current workspace Research-read decision from LQ-2660
with the persistent bounded index boundary from LQ-2663.

The result is an application operation only. It introduces no HTTP route,
document rendering, serialization, edge rule, or deployment behavior.

## Inputs and authority

`list_current_workspace_research_jobs` receives the current-workspace lookup,
membership lookup, authorized index port, and authenticated
`SessionPrincipal`.

The principal identifies the actor but grants no authority. The operation
resolves the actor's current workspace from the system of record and performs
a fresh Research-read decision before any index lookup.

No caller-supplied WorkspaceId, allow boolean, role, permission collection,
capability, limit, cursor, filter, or ordering value enters the operation.

## Binding

When current authority exists, the operation passes exactly the principal's
internal UserId and the freshly resolved WorkspaceId to the index port.

It never derives authority from a returned JobId, job authorship, browser
input, stale page, cached result, or ordinary authentication.

An absent current workspace, mismatched context actor, inactive authority
fact, or missing Research-read permission prevents the index call entirely.

## Observable outcomes

The internal application outcome has three deliberately separate forms:

- a tuple of minimal index items means an authorized non-empty page;
- an empty tuple means an authorized workspace currently has no visible jobs;
- `None` means neutral absence or rejection before the index was read.

The neutral outcome does not disclose whether workspace context, user,
workspace, membership, permission, or actor binding caused rejection.

The operation does not expose total counts, invisible rows, another
workspace, additional pages, or why no authority exists.

## Technical unavailability

Workspace-context, membership, and Research-job store failures propagate
through their existing detail-free technical-unavailability boundaries.

They are not translated into `None`, an empty tuple, a partial tuple, cached
content, or a newly named public exception.

Transport mapping remains a later responsibility and must preserve the
difference between neutral rejection and technical unavailability.

## Freshness and revocation

Every call repeats current-workspace resolution, membership authorization,
and persistent index lookup.

A committed session revocation is enforced by the enclosing authenticated
entry point. User, workspace, or membership deactivation and permission
removal affect the next application call through fresh system-of-record
reads.

No decision or index page is cached by this composition. A prior successful
result grants no later authority.

## Verification

Tests prove exact actor/workspace binding, authorized non-empty and empty
results, neutral denial, absent and mismatched context fail-closed behavior,
and unchanged propagation of each technical-unavailability category.

They also prove that denied requests never invoke the Research-job index.

## Explicit non-goals

This slice creates or mutates no user, workspace, membership, role,
permission, capability, admission, session, Research job, result, claim,
lease, artifact, or identity fact.

It adds no schema, table, column, SQL, migration, persistence implementation,
bootstrap behavior, CLI, worker, configuration, cache, or pagination.

It adds no HTTP path, HTML, JSON, link, status mapping, middleware, cookie,
edge configuration, release, promotion, or staging acceptance.

## Next step

A later transport slice may render this operation on the already authorized
exact `/research` surface while preserving neutral denial, authorized empty,
and detail-free technical unavailability. Persistent wiring and staging
exposure remain separate decisions.
