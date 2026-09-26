# LQ-2690 — Staging Research-index session-acquisition contract

## Outcome

This slice defines the narrow contract by which a later trusted integration may
acquire the complete LQ-2688 session handoff. It introduces an opaque session-
set identifier, an opaque expected revision, a bound acquisition result, and a
single acquisition capability.

Neither identifier is a credential or an authority fact. The session-set handle
selects one pre-provisioned operational set; the expected revision prevents a
caller from silently accepting a rotated or replaced set. Both values are
opaque, canonical, bounded, and absent from representations.

## Observable contract

Acquisition accepts only the session-set handle and its expected revision. It
accepts no user, workspace, role, membership, permission, capability, provider
claim, or allow boolean from the caller.

A successful result repeats the exact identifier and revision and carries one
already validated session handoff. The explicit validator rejects substitution
of either binding. The handoff itself continues to require the complete closed
slot inventory and the same session before and after fixture revocation.

Neutral absence is represented by no acquired set. This covers an unknown,
inactive, revoked, stale, incomplete, or otherwise unusable configured set
without disclosing which condition applied. Technical inability may fail the
acquisition call; higher composition must reduce that failure to its existing
detail-free unavailable outcome.

Any later adapter must resolve session-set lifecycle and current revision from
its trusted system of record. Revocation or rotation must affect later calls;
cached caller assertions cannot override current state.

## Exclusions

LQ-2690 does not choose an identity provider, login flow, browser driver,
credential vault, secret format, storage schema, table, SQL statement, migration,
port implementation, CLI, environment variable, retry, scheduler, deployment,
or promotion. It creates no users, workspaces, memberships, roles, capabilities,
credentials, or sessions. Persistent registry and acquisition implementation
remain explicit later slices.
