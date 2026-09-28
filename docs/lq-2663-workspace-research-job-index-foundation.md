# LQ-2663 – Workspace Research-job index foundation

## Result

LQ-2663 implements the minimal internal item, read-only port, and persistent
adapter required by the LQ-2662 workspace Research-job index contract.

It reuses the existing persistent Research-job tables and
`DatabaseResearchJobs`. No schema or migration is added.

## Internal item

`ResearchJobIndexItem` carries exactly:

- the stable opaque `JobId`;
- the controlled `ResearchJobStatus`;
- the committed acceptance time;
- the committed last-update time.

Its JobId is excluded from representation. The item has no workspace, actor,
revision, acceptance, worker, claim, lease, artifact, experiment, strategy,
dataset, result, or failure-detail field.

Both timestamps must be aware UTC values, and update time cannot precede
acceptance time. Invalid persistent values fail through the existing technical
store-unavailability boundary.

## Read-only port

`AuthorizedWorkspaceResearchJobIndex` exposes one operation accepting only the
internal actor UserId and server-resolved WorkspaceId.

It accepts no browser session, cookie, CSRF token, allow boolean, role, status,
permission set, capability, caller-controlled limit, ordering, filter, cursor,
or time range.

The returned value is an immutable tuple of `ResearchJobIndexItem` values. An
empty tuple is the authorized empty result and performs no mutation.

## Persistent binding

`DatabaseResearchJobs.list_jobs` resolves the current authority and result in
one database statement.

The statement requires the supplied internal actor to be active, the target
workspace to be active, their ordinary membership to be active, and that
membership to have `research:read` or `research:write`.

Every selected job is constrained to the exact same WorkspaceId. The adapter
does not fetch a global queue and filter it in process memory.

The method does not use the job's accepting actor as an access shortcut.
Workspace Research-read authority controls the shared workspace view, while
job authorship grants nothing by itself.

## Bounded deterministic page

The adapter owns a fixed first-page maximum of 50 jobs. No caller input can
increase or disable the bound.

Rows are ordered by committed acceptance time descending and opaque JobId
descending as the stable tie-breaker.

No total count, continuation marker, invisible-row indication, or second page
is produced.

## Absence, denial, and unavailability

An authorized workspace without jobs returns the empty tuple.

Inactive user, inactive workspace, inactive membership, absent Research-read
authority, or a different workspace also produces no visible rows. The adapter
does not disclose which authority fact failed.

The enclosing application remains responsible for distinguishing an authorized
empty page from neutral route-level denial by authorizing the current workspace
before invoking or rendering the index.

Malformed stored values, database failures, and unsupported persistence
behavior use the existing detail-free `ResearchJobStoreUnavailable` boundary.
They are not converted into an empty authorized page by the adapter.

## Freshness and revocation

Every call executes a new database read against current identity, workspace,
membership, permission, and job facts.

There is no session, application, adapter, or process cache. A committed
permission removal or user, workspace, or membership deactivation hides the
entire index on the next call.

A returned tuple conveys no authority for a later detail request. A JobId from
the tuple remains navigation identity only.

## Verification

Tests prove the item's minimal shape and timestamp invariants, the exact port
signature, workspace isolation, deterministic ordering, server-owned bound,
authorized empty result, and fresh effects of all current authority
revocations.

Existing persistent Research-job acceptance, claim, heartbeat, detail lookup,
composition, and type tests remain green.

## Explicit non-goals

This slice adds no application orchestration, HTTP route, HTML rendering,
serialization, job link, pagination, filter, search, edge rule, deployment, or
staging acceptance.

It creates or mutates no user, workspace, membership, role, permission,
capability, admission, identity binding, session, Research job, result, claim,
lease, or artifact.

It adds no schema, table, column, index, migration, bootstrap behavior, CLI,
operator command, background process, cache, or configuration value.

## Next step

A later application slice may compose the current workspace Research-read
decision with this port and preserve the difference between authorized empty,
neutral denial, and technical unavailability. HTTP rendering remains a
separate slice after that composition is tested.
