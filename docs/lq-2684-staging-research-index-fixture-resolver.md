# LQ-2684 — Persistent staging Research-index fixture resolver

## Outcome

This slice supplies the persistent read-only resolver required by LQ-2683.
An opaque fixture handle can identify one pre-provisioned staging fixture, but
the handle itself carries no authority and exposes no identity information.

Resolution reads the actor, target user, target workspace, original active
membership revision, and its research permissions from the system of record.
It never accepts a caller-supplied actor, target, workspace, role, permission,
membership, or allow boolean.

## Fail-closed resolution

The resolver returns a binding only when the actor and target user are active,
the workspace is active, and the actor currently holds the separate active
workspace membership-management capability. Authentication represented by the
returned `SessionPrincipal` identifies the actor; it does not grant authority.

The recorded revision must be an active full membership snapshot for exactly
the recorded target and workspace and must contain at least one research
permission. Research permissions are data restored by fixture control, not
membership-management authority.

Unknown handles and bindings made unavailable by lifecycle or authority
revocation resolve neutrally to absence. Storage failure or structurally
unusable persisted state becomes the existing detail-free fixture-control
unavailability. No storage, identity, or authority detail crosses the boundary.

Every call reads current system-of-record facts. There is no authority cache,
so later actor, target, workspace, or management-capability revocation affects
later decisions. The historical original active membership snapshot remains
readable after the current membership advances to its revoked revision, which
is necessary for a correctly bound restore.

## Persistence boundary

The migration adds only a durable binding registry for fixtures provisioned
outside this runtime slice. Fixture identities are non-empty and non-reusable;
one active revision and one target/workspace pair cannot be reassigned to
another fixture. Foreign-key bindings preserve the stable internal identity
and revision facts on which resolution depends.

The resolver has no create, update, delete, admission, bootstrap, user,
workspace, membership, role, capability, credential, deployment, or promotion
operation. It does not alter the current membership and does not provision test
facts. Retention of the fixture binding and referenced historical revision must
be at least as long as any revocation/restore workflow that may rely on them;
their identities must never be recycled during or after that retained history.

## Deferred work

How staging facts are safely pre-provisioned remains a separate operational
slice. Real fixture execution, evidence acquisition, deployment, promotion,
cleanup, and ordinary membership or capability administration also remain
outside LQ-2684.
