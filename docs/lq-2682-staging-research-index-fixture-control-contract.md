# LQ-2682 — Staging Research-index fixture-control contract

## Outcome

This slice defines the opaque, revision-bound control contract needed to revoke
and restore one pre-provisioned staging Research-index acceptance fixture.

## Fixture identity

The fixture is referenced only through an opaque bounded identifier. The
contract carries no user identifier, workspace identifier, membership, role,
permission, session, credential, URL, or caller-supplied authorization fact.
The opaque identifier is a lookup handle, not authority.

## Revocation

Revocation is a distinct injected capability. It accepts the opaque fixture
identifier and the exact active revision expected by the controller. A
successful result binds the same fixture, that active revision, and a distinct
new revoked revision. Stale or mismatched revisions cannot be represented as a
successful transition.

## Restoration

Restoration is a separate injected capability and accepts the completed
revocation binding rather than free-form target facts. Its result binds the
same fixture and revoked revision to a distinct restored revision. Validation
rejects a different fixture, a different revoked source, or reuse of either the
active or revoked revision.

Neither operation accepts an `allow` boolean or role. Implementations must
resolve the fixture target and mutation authority from their system of record
and preserve the existing membership-management authorization boundary.

## Exclusions

This slice defines no database adapter, SQL, schema, migration, CLI, credential
source, fixture creation, user creation, workspace creation, membership
creation, retry, scheduling, or workflow. It performs no mutation itself and
does not connect the capabilities to real staging.

Fixture-control results contain no acceptance evidence and grant no promotion
authority. The LQ-2681 evidence composition remains unable to revoke or restore
without an explicitly supplied later implementation.

## Next slice

A later slice may implement the fixture controller by adapting the existing
authorized membership-management mutation and system-of-record lookup. Real
staging execution and promotion remain separate.
