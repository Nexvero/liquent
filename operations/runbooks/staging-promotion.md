# Staging promotion and application rollback

This runbook is intentionally operator-driven. It does not authorize a
production deployment and never accepts an image tag as deployment identity.

## Preconditions

1. `registry-release` completed and produced `release-manifest.json`.
2. Resolve the published reference as
   `ghcr.io/nexvero/liquent@sha256:<digest>`.
3. Produce fresh staging backup evidence containing `snapshot_id=` and an UTC
   `verified_at=` value after a successful backup verification.
4. Install a root-owned `/etc/liquent/deploy.env` from
   `operations/deploy/deploy.env.example` with mode `0600`.
5. Ensure the Compose contract, runtime settings, secrets, external networks,
   edge routing and previously healthy staging digest exist.

## Preflight

Run the promotion tool with `--check` first. It validates configuration,
HTTPS health URL, previous rollback digest, release-manifest binding and backup
evidence without creating state or invoking Docker.

## Promotion

The apply run takes a host lock, journals the previous and candidate digests,
pulls by digest, validates Compose, waits for PostgreSQL, runs the one-shot
migration gate, replaces only the control plane, and then requires the external
HTTPS liveness response. Failure restores the previous image configuration and
attempts an application rollback.

## Rollback

Use `rollback-staging.sh <run-id>`. It accepts only a recorded run ID and its
validated previous digest. Rollback changes the application image only.
Database migrations are deliberately never reversed automatically; every
migration reaching staging must therefore remain compatible with the previous
application version.

## Required evidence

Record the release run, deployment run ID, previous and candidate digests,
backup snapshot ID, migration result, internal container health, external HTTPS
result, operator and decision. A first-ever staging deployment without a known
healthy previous digest is intentionally outside this automation and requires a
separate bootstrap procedure.
