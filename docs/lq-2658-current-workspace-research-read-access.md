# LQ-2658 – Current workspace research-read access

## Result

LQ-2658 adds an application-level authorization composition for a future
read-only Research entry from the current workspace context.

It returns a current workspace context only after both the LQ-2656 context
resolver and the existing research authorization policy allow the same actor
and workspace.

## Decision sequence

The use case accepts a resolved `SessionPrincipal`, a current-workspace lookup,
and the existing workspace-membership lookup.

First, the actor's current workspace is resolved without caller selection. If
there is no unique context, the result is neutral `None` and no membership
lookup occurs.

Second, the returned context actor must exactly match the session actor. A
mismatched dependency result fails closed before membership resolution.

Third, the existing `authorize_research` application boundary resolves the
current membership for that exact actor and workspace and requires
`research:read`.

The established policy continues to let `research:write` imply read access,
while read access never implies write access.

## Result semantics

Success returns the same immutable `CurrentWorkspaceContext`. The result is an
internal navigation prerequisite, not a general authority token.

Missing or ambiguous context, missing or inactive membership, absent Research
permission, and mismatched identities all produce the same neutral `None`.
The result reveals no reason, identifier, count, role, or capability.

Technical context or membership-store unavailability propagates through the
existing detail-free boundary. It is not converted into a denial or absence.

## Freshness and revocation

Each invocation resolves the workspace context and membership again. No
session, route, browser, or application cache stores the decision.

Committed user, workspace, or membership deactivation and committed Research
permission revocation therefore affect the next invocation.

The `SessionPrincipal` identifies only the actor. Neither successful login nor
workspace visibility supplies Research authority.

## Authority separation

The use case reads only ordinary membership and explicit Research permissions.
It does not inspect or infer onboarding-, membership-, lifecycle-, or other
management capabilities.

Success cannot authorize a Research write, job start, membership mutation,
workspace mutation, or administrative operation. Every such action retains its
own current authorization boundary.

## Verification

Tests prove exact actor/workspace binding, explicit read permission, the
existing write-implies-read rule, early stop without context, neutral handling
of every denial, mismatched dependency rejection, and propagation of technical
unavailability.

## Explicit non-goals

This slice adds no HTTP route, link, HTML, job list, persistent Research job,
workspace chooser, edge exposure, schema, migration, adapter, CLI, operator
command, bootstrap, or mutation.

It creates or changes no user, workspace, membership, permission, capability,
authority, session, admission, or identity binding.

## Next step

A later slice may use this application decision to render a detail-free
Research-read entry on the workspace-aware landing. The linked destination and
its resources must retain their own target-bound authorization checks.
