# LQ-2666 – Workspace Research-job index persistent wiring

## Result

LQ-2666 supplies the existing `DatabaseResearchJobs` index capability to the
LQ-2665 HTTP renderer whenever the control plane has a database engine.

The index uses the same engine as persistent sessions, current-workspace
resolution, memberships, and other database-backed control-plane components.

## Composition rule

When an engine is present and no explicit index dependency was supplied, the
application creates one `DatabaseResearchJobs` adapter and exposes it only
through the read-only workspace-index protocol.

When an explicit index dependency is supplied, it retains precedence. This
keeps isolated tests and deliberate embedding compositions deterministic.

Without a database engine, no persistent index is inferred and the existing
in-memory/detail-free behavior remains unchanged.

## Read-only boundary

The automatically composed adapter is reachable by the `/research` renderer
only as `AuthorizedWorkspaceResearchJobIndex`.

Its mandatory mutation identifiers are fail-closed placeholders that raise
the existing Research-job store-unavailability boundary if unexpectedly
invoked. The HTTP index path cannot invoke acceptance, claiming, lease,
completion, or failure operations.

No write capability, runner, worker, artifact store, or mutation endpoint is
enabled by this composition.

## Authority and data binding

The browser session identifies the actor but grants no authority. Each request
still resolves the current active workspace and current Research-read
membership before reading the index.

The persistent adapter independently binds that actor and WorkspaceId to
active system-of-record facts in its bounded query. No caller-supplied allow
value, role, workspace, filter, or page size enters the wiring.

## Freshness and revocation

The composition creates no authority or result cache. The same adapter issues
a fresh database read for every accepted request.

Committed user, workspace, or membership deactivation and Research permission
removal affect the next request. Session revocation remains enforced by the
existing persistent session lookup before application composition.

## Failure behavior

Persistent context, membership, session, and job-index failures continue
through their existing detail-free technical-unavailability boundaries.

The wiring does not translate them into an empty page, neutral denial, stale
page, partial result, or new exception name.

## Verification

An integration test migrates one isolated database, seeds active identity,
workspace, membership, Research-read permission, session, and job facts, then
proves that `/research` renders the persistent job.

A second request after committed permission removal proves fresh revocation.
Another test proves explicit dependency precedence.

## Explicit non-goals

This slice adds no schema, table, column, index, SQL statement, migration,
identity fact, authority fact, Research job, session, or bootstrap mutation.

It adds no job submission, detail, evidence, cancellation, retry, deletion,
pagination, filter, search, worker, artifact, or cache behavior.

It changes no edge rule, public path, release format, deployment, promotion,
secret, DNS record, or staging environment.

## Next step

A later release slice may package and promote this persistent read-only page
through the already exact staging edge. Real staging acceptance must verify
login, authority, empty and non-empty rendering, revocation, and unavailable
behavior without creating a new mutation surface.
