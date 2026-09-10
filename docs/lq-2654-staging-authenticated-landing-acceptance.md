# LQ-2654 — Staging Authenticated Landing Acceptance

## Purpose

This slice records the controlled staging acceptance of the authenticated
post-login landing introduced by LQ-2653. It binds the observed browser result
to one reviewed main revision, immutable release image, verified backup, and
completed promotion.

This is an evidence checkpoint. It changes no runtime behavior and grants no
authority.

## Bound revision and release

Pull request `#154` passed all required checks without a base-branch conflict
and was squash-merged to `main` as revision
`424d8a5b8437bc0e587bbd667f1a15bb5b822149`.

Post-merge quality run `34438164155` completed successfully in 8 minutes and
53 seconds. Its test, PostgreSQL integration, wheel, application container,
backup container, and provenance jobs all succeeded. The run produced the
expected supply-chain and wheel artifacts plus an attestation.

Controlled release run `34440635920` published version `0.1.12` from exactly
that revision. The immutable application image is:

`ghcr.io/nexvero/liquent@sha256:06cbf435edb2266d9ab2be6593fad5ba3584e39a74a9282da947611acff0d706`

The release manifest binds the version, full revision, image repository, image
digest, and SBOM digest. The publication job completed successfully and
created its release attestation and evidence artifact.

## Backup and rollback gate

Before promotion, the hardened staging backup container created encrypted
snapshot `ab25235e`. Repository metadata, packs, snapshots, trees, and blobs
passed the repository check.

The snapshot was restored into an isolated container target. The restored
database dump matched its recorded checksum and `pg_restore` accepted its
catalog. No database import or application mutation occurred during this
verification.

The release manifest and fresh backup evidence passed the read-only deployment
preflight. A previously healthy immutable application digest remained
available as the rollback point.

## Promotion result

Promotion run `20260910T054619Z-1938158` pulled only the manifest-bound image
digest, retained PostgreSQL health, passed the migration gate, replaced only
the control plane, and completed its external HTTPS liveness check.

The deployment journal records `complete`. PostgreSQL and the control-plane
container both report `healthy`, and the running control-plane image is the
exact `0.1.12` digest above.

No production environment was selected or changed.

## Edge binding

The exact LQ-2653 root location required a separate controlled edge reload
because normal application promotion intentionally replaces only the control
plane.

The previously active edge file was retained as a rollback copy. The candidate
and active Nginx configuration passed `nginx -t` before reload. The installed
edge file is byte-identical to `operations/edge/staging.conf`; both have
SHA-256:

`e9bece32910f30ed2d33ff4170e845b3862b472376d126932a880f290c8923cb`

The only difference from the preceding active edge file was the additive exact
root proxy. The broad catch-all continues to return 404.

## Public smoke acceptance

The public liveness, login, neutral rejection, and technical-unavailability
documents each returned HTTP 200 after promotion.

A request to `/` without a browser session returned HTTP 303 with location
`/login`, `no-store`, and `no-referrer`. This confirms neutral session absence
without exposing user, identity, workspace, admission, or session history.

The existing authenticated browser session then requested the same root path
and received the static LQ-2653 document:

- `Signed in to Liquent`;
- `Your authenticated session is active.`

The browser did not receive an edge 404, an empty document, or a downloaded
file. The result therefore closes the concrete post-callback failure observed
before LQ-2653.

## Authority boundary

The accepted page proves only that the browser presented a session which the
current persistent session system resolved as active. The session principal
identifies the actor and grants no authority by itself.

The page does not select or reveal a workspace. It does not establish ordinary
membership, onboarding-management capability, role, research permission, or
any other application entitlement.

No caller-supplied allow flag, role, user identifier, workspace identifier, or
target is accepted by the route. Revocation or expiry remains effective for
later requests through a fresh system-of-record session lookup.

## Mutations and non-goals

The acceptance operation created no user, workspace, admission, external
identity binding, membership, role, capability, or research permission. It
performed no regular authority mutation and changed no persistent identity
fact.

This slice adds no schema, table, SQL, migration, port, model, signature, CLI,
provider, secret, or application wiring decision. It does not implement a
product dashboard, workspace selection, navigation, onboarding controls, or
research UI.

## Next slice

LQ-2655 should define the first workspace-aware authenticated read surface. It
must resolve the actor and target workspace from persistent system-of-record
facts, keep SessionPrincipal non-authorizing, and distinguish neutral absence
from detail-free technical unavailability.

That slice must not invent membership or capability persistence. If the
required regular membership or capability facts are not yet implemented, the
surface must fail closed and leave their persistence and mutation to explicit
later slices.
