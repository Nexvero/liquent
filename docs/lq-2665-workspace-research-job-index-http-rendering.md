# LQ-2665 – Workspace Research-job index HTTP rendering

## Result

LQ-2665 renders the LQ-2664 application result on the existing exact
`GET /research` browser surface.

The route remains read-only, session-authenticated, current-workspace bound,
and protected by a fresh Research-read decision.

## Rendered information

Each visible row contains only the stable opaque JobId, controlled status,
and committed last-update time supplied by the bounded index item.

The document contains no UserId, WorkspaceId, membership, role, permission,
revision, claim, lease, worker, artifact, result, evidence, failure detail,
CSRF value, session identifier, or persistence detail.

Rows have no detail, evidence, mutation, cancellation, retry, or deletion
link. Those actions and destinations require separate contracts.

## Exact transport surface

Only the already established exact path `/research` renders the index.

The method remains GET-only. Query strings, caller-selected workspace,
limits, cursors, filters, search, ordering, and status selection are rejected
before authentication or index access.

No prefix route, trailing-slash alias, subpath, rewrite, fallback, or new API
endpoint is introduced.

## Outcomes

An authorized non-empty page renders the bounded ordered rows. An authorized
empty tuple renders a successful empty state without implying invisible jobs
or further pages.

Neutral absence or rejection remains a bodyless 404 with no authority detail.
Authentication failure retains the existing login redirect behavior.

Workspace, membership, or Research-job store failure retains the existing
detail-free redirect to the unavailable destination. No partial page, stale
page, empty success, or new public exception is substituted.

## Browser safety

The response remains `text/html` with `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`.

Every rendered persistent value is HTML-escaped. The page contains no script,
form, mutation control, caller-reflected input, externally loaded resource,
or authority-bearing browser state.

## Freshness and revocation

Every request resolves the browser session, current workspace, membership,
Research-read authority, and persistent index again.

Committed session revocation, lifecycle deactivation, or permission removal
therefore affects the next request. Browser history and previously rendered
JobIds confer no later authority.

## Compatibility

The index renderer is enabled only when its explicit application dependency
is supplied. Existing isolated consumers without that dependency retain the
previous detail-free Research landing document.

This permits transport verification before persistent production wiring is
introduced in a separate slice.

## Verification

Tests prove non-empty and empty rendering, minimal visible fields, exact
actor/workspace binding, detail-free denial, technical unavailability,
security headers, absence of detail links, and query rejection before lookup.

The established Research destination tests remain unchanged and green.

## Explicit non-goals

This slice creates or mutates no identity, authority, session, workspace,
membership, Research job, result, claim, lease, artifact, or admission fact.

It adds no schema, table, column, SQL, migration, persistence adapter,
bootstrap, CLI, worker, cache, pagination, filter, or search behavior.

It adds no job detail, evidence rendering, submission, cancellation, retry,
deletion, release, edge rule, deployment, promotion, or staging acceptance.

## Next step

A later wiring slice may supply the persistent LQ-2663 index adapter to this
HTTP dependency in the database-backed control-plane composition. Edge and
real staging acceptance remain separate follow-up slices.
