# LQ-2662 – Workspace Research-job index contract

## Result

LQ-2662 defines the observable contract for the first persistent Research-job
index reachable from the workspace-bound read destination.

The index is read-only. This slice does not add a route, port, model, adapter,
query, schema, migration, HTML document, API response, or deployment change.

## Purpose

An authorized actor needs a bounded view of persistent Research jobs belonging
to the actor's current workspace.

The index is not a global queue, worker console, operations dashboard, artifact
browser, audit export, or job-submission surface.

It reports only committed job facts that the persistent Research-job system of
record considers visible at the time of the request.

## Request authority

The browser session identifies the actor through the current
`SessionPrincipal`. It grants no workspace or Research authority.

The application must resolve exactly one current workspace for that actor from
active user, workspace, and ordinary-membership facts. The caller cannot
supply, replace, or widen that WorkspaceId.

For the same actor and resolved workspace, the application must freshly require
an active membership carrying `research:read`. The existing
`research:write`-implies-read rule may satisfy that check, while read authority
never implies write authority.

No caller-supplied allow boolean, role, status, permission set, capability,
membership snapshot, user identifier, or workspace identifier is accepted as
authority.

## Target binding

The persistent lookup must bind every returned job to the resolved current
workspace in the system of record.

It must not load a global set and filter it only in application memory. It must
not trust a workspace copied from the session, URL, cursor, browser state, job
snapshot, cache, or previously rendered page.

A job whose persistent workspace differs from the resolved workspace is never
part of the result, even if the same actor originally accepted it.

Jobs belonging to other users may be visible only through the workspace's
current Research-read policy. Ownership of a job is not a substitute for
current workspace authority, and authorship does not bypass revocation.

## Visible item

Each item may reveal only the minimum navigation facts:

- one stable opaque `JobId`;
- the current controlled job status;
- committed acceptance time;
- committed last-update time.

The current workspace identifier is omitted because the whole result is already
bound to one server-resolved workspace. Actor identifiers and revision,
acceptance, claim, lease, worker, and artifact identifiers are also omitted.

The first index does not reveal experiment inputs, strategy parameters, data
references, fingerprints, titles, result summaries, failure diagnostics,
artifact keys, checksums, sizes, internal paths, or exception details.

An item's `JobId` is navigation identity only. A later detail request must
resolve that job and repeat current actor, workspace, and Research-read checks.

## Ordering and boundedness

The first page is bounded by a server-owned maximum. The caller cannot request
an unbounded result or increase the maximum through a query, header, cookie, or
body.

Ordering is deterministic: newer committed acceptance time first, with stable
opaque JobId as the tie-breaker. Database default order and process-memory order
are not observable contracts.

The first implementation may expose only this bounded initial page. Pagination,
continuation cursors, filtering, search, sorting choices, status selection, and
date ranges remain later contracts.

No total job count is required. The response must not reveal that invisible
jobs, other workspaces, or additional pages exist.

## Absence and denial

An authorized workspace with no visible committed jobs produces a successful
empty index.

No current workspace and missing or revoked Research-read authority use the
same neutral rejection as the enclosing Research surface. They do not produce
an empty list that could be confused with an authorized result.

The public outcome does not distinguish an inactive user, inactive workspace,
inactive membership, missing permission, ambiguous context, actor mismatch, or
unknown relationship.

A job changing concurrently after the lookup may appear with either committed
state surrounding the read, but no partially committed job or outcome may be
reported.

## Technical unavailability

Session, workspace, membership, and Research-job store failures produce the
existing detail-free technical-unavailability outcome.

Technical unavailability must not be translated into an empty index, neutral
authorization rejection, stale cached result, or partially successful page.

No new public exception name, database diagnostic, SQL text, DSN, table name,
host detail, stack trace, or retry promise is introduced by this contract.

## Freshness and revocation

Every request resolves the session, current workspace, Research permission,
and persistent job page again.

Committed session revocation, user or workspace deactivation, membership
deactivation, and permission removal affect the next decision. A previously
visible page, link, JobId, or browser history entry grants no later access.

The application must not cache the authority result in the session, route,
process, rendered document, or job-index adapter.

## Identity retention lower bounds

`UserId`, `WorkspaceId`, and `JobId` remain stable internal facts and are never
reassigned to a different entity.

Their identity anchors and the minimum tombstone or lineage evidence needed to
prevent reuse must outlive deactivation and ordinary operational cleanup.

This is a retention and non-reuse lower bound, not a concrete table, column,
foreign-key, archival, deletion, partition, or backup policy.

## Authority separation

Research-read authority allows only this read view and later separately
authorized detail reads.

It grants no job acceptance, execution, cancellation, retry, deletion,
artifact publication, admission, onboarding management, membership management,
role management, user lifecycle, workspace lifecycle, or deployment authority.

Ordinary membership, Research permissions, and management capabilities remain
separate persistent facts with separate mutation and revocation boundaries.

## Explicit non-goals

This slice creates or mutates no user, workspace, membership, role, capability,
permission, session, identity binding, admission, Research job, outcome, claim,
lease, artifact, or authority fact.

It makes no schema, table, SQL, port, model, function-signature, migration,
route, serialization, template, CLI, test, wiring, edge, cache, pagination,
release, promotion, or staging decision.

Job submission, details, evidence, result presentation, filtering, pagination,
and operational queue inspection remain separate slices.

## Next step

A later implementation slice may introduce the minimal internal item and
read-only persistence boundary required by this contract. HTTP rendering and
staging exposure must remain separate decisions after that implementation is
verified.
