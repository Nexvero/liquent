# LQ-2656 – Current workspace context resolver

## Result

LQ-2656 implements the narrow read-only resolver required by LQ-2655. It
derives at most one current workspace context from the authenticated actor's
stable internal `UserId` and current persistent facts.

The slice adds an immutable internal result, a structural lookup port, and a
persistent adapter. It exposes no browser route and performs no mutation.

## Internal result

`CurrentWorkspaceContext` binds exactly one `UserId` to one `WorkspaceId`.
Both values remain internal, stable, and non-reassignable.

The result is not an authorization decision. It contains no role, permission,
capability, membership status, provider claim, session value, or allow flag.

Receiving a context does not authorize research access, onboarding management,
membership management, lifecycle management, or any future operation.

## Lookup boundary

`CurrentWorkspaceContextLookup.resolve_current_workspace(user_id)` accepts only
the internal actor identity. It accepts no target workspace and therefore
cannot honor caller-selected workspace context.

The port returns one immutable context or neutral `None`. It does not list,
rank, paginate, search, or reveal candidate workspaces.

Session resolution remains outside this port. A later application or HTTP
composition may pass only the actor from a currently resolved
`SessionPrincipal`.

## Persistent resolution

`DatabaseCurrentWorkspaceContexts` reuses the existing identity-user,
identity-workspace, and workspace-membership foundations. No schema or
migration is added.

One context is returned only when the system of record currently contains:

- the requested user in the exact active state;
- exactly one workspace in the exact active state;
- exactly one active ordinary membership binding that user and workspace.

Zero eligible rows return neutral `None`. More than one eligible row also
returns the same neutral `None`; the adapter never selects the first row or
uses storage ordering as product policy.

Inactive users, workspaces, and memberships are excluded from eligibility.
Inactive or unrelated rows cannot make an otherwise ambiguous result eligible.

## Freshness and revocation

Every call reads current committed facts through the supplied database engine.
There is no process, session, route, or adapter cache.

A committed user, workspace, or membership deactivation therefore changes the
next resolution. A previous context object cannot be reused as authority and
does not freeze visibility until session expiry.

## Neutral absence and technical unavailability

Neutral `None` does not distinguish unknown actor, inactive actor, no active
membership, inactive workspace, inactive membership, or multiple eligible
memberships. It reveals no count or identifier.

Database failure, missing migration, malformed identifier input, invalid byte
encoding, or an unreconstructable stored identifier is not converted to
absence. The adapter uses the existing detail-free
`WorkspaceMembershipStoreUnavailable` boundary.

The exception and adapter representation disclose no user, workspace,
membership, SQL, table, constraint, driver, host, port, or DSN detail.

## Separation from authority

The resolver does not read research permissions because permissions are not
needed to establish a neutral workspace context.

Every downstream research read must still resolve current membership and the
required research capability through the existing authorization chain.

Onboarding-, membership-, and lifecycle-management authorities remain separate
persistent facts. None is inferred from the returned ordinary membership
context.

## Verification

Tests prove structural port compatibility, exact single-context reconstruction,
neutral absence for inactive foundation facts, neutral ambiguity for multiple
active memberships, and the effect of a later committed deactivation.

An unmigrated database proves detail-free technical unavailability. Existing
membership and research-authorization regression tests remain green.

## Explicit non-goals

This slice creates or mutates no user, workspace, admission, identity binding,
membership, role, capability, permission, session, or authority fact.

It adds no schema, migration, route, HTML, status code, cookie behavior, edge
exposure, CLI, operator command, bootstrap, workspace chooser, or fallback.

It does not decide how multiple memberships become selectable. That requires a
separate explicit product and authority contract.

## Next step

A later slice may compose the current authenticated landing with this resolver
and render a detail-free workspace-aware read document. That route must retain
LQ-2653 session behavior, reject caller-selected workspaces before lookup, and
keep every linked operation behind its own current authorization decision.
