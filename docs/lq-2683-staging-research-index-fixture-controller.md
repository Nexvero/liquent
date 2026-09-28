# LQ-2683 — Staging Research-index fixture controller

## Outcome

This slice adapts the opaque LQ-2682 fixture-control contract to the existing
authorized complete-membership-change boundary.

## Resolution and authority

The caller supplies only the opaque fixture handle and expected active revision.
An injected system-of-record resolver supplies the authenticated management
actor, target user, target workspace, active membership revision, status, and
complete permission snapshot. The handle itself grants no authority.

The controller never accepts caller-provided user IDs, workspace IDs, roles,
permissions, membership state, or allow booleans. The existing membership
change implementation remains responsible for resolving current management
authority and active user, workspace, and target facts atomically.

## Revocation and restoration

Revocation requires the caller's expected revision to equal the resolved active
revision, then writes an active membership with an empty complete permission
set. Restoration re-resolves the fixture, verifies the original active revision,
and restores the exact system-of-record status and permission snapshot against
the committed revoked revision.

Each transition receives a new non-reusable change identifier and must return a
new committed membership revision. Missing fixtures, stale bindings, rejected
changes, malformed results, and technical failures collapse to one detail-free
control-unavailable result.

## Exclusions

This slice adds no fixture registry, database table, SQL, schema, migration,
CLI, credential source, fixture creation, user or workspace creation, retries,
scheduling, evidence mutation, deployment, or promotion. The resolver and real
persistent wiring remain separate.

## Next slice

A later slice may implement persistent fixture resolution for pre-provisioned
staging facts. Real execution and promotion remain separate.
