# LQ-2688 — Staging Research-index session handoff

## Outcome

This slice introduces one validated, opaque session handoff for an explicitly
controlled staging Research-index acceptance run. The handoff closes the
remaining boundary between externally acquired browser sessions and the
LQ-2687 runtime composition.

Construction requires the complete three-stage inventory before execution can
begin. The baseline stage requires the empty-workspace, visible-workspace, and
revocation-fixture readers. The after-revocation stage requires only the
revocation-fixture reader. The technical-unavailability stage requires only
its dedicated reader. Missing stages or slots, surplus entries, the anonymous
slot, wrong key types, and non-opaque values are rejected.

## Revocation observation binding

The before- and after-revocation observations must carry the same opaque
session value. This makes the later decision observe revocation for the same
authenticated browser session instead of allowing a caller to substitute a
different identity after mutation.

The session remains identification material only. It supplies no role,
membership, permission, management capability, or allow decision. Authority
continues to be resolved from the system of record by the existing persistent
fixture-control path on every mutation decision.

The accepted inventory is defensively copied and cannot be changed through a
mutable caller-owned mapping. Each execution receives a fresh mapping in the
already established LQ-2685 shape. Representations disclose no opaque session
material.

## Runtime boundary

LQ-2687 now accepts the validated handoff rather than an arbitrary nested
mapping. Full inventory and cross-stage identity binding therefore complete
before database mutation, HTTP acquisition, restoration, or evidence
publication can occur. The controlled executor retains its existing exact
per-stage checks as a second boundary.

## Exclusions

LQ-2688 creates, refreshes, persists, revokes, or discovers no login session.
It reads no credential source or environment variable and adds no login
automation, schema, migration, fixture provisioning, CLI, scheduler, retry,
deployment, or promotion. Session acquisition, controlled operation, and real
promotion remain separate.
