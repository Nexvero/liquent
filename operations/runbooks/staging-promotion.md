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

## Research-index unknown-effect reconciliation

This is a separate, manual recovery action. Do not run it during the normal
application promotion or rollback flow. Use it only when the durable staging
research-index promotion journal already contains an unknown-effect attempt and
the operator has independently confirmed that reconciliation is required.

Prepare two absolute, non-root, owner-held regular files. Both files must have
mode `0600`, one hard link, no symbolic-link traversal, UTF-8 content and a
trailing newline. The provider settings file contains exactly:

```text
LIQUENT_STAGING_PROMOTION_PROVIDER_ENDPOINT=https://PROVIDER_HOST/STATUS_PATH
```

The process settings file contains exactly:

```text
LIQUENT_STAGING_PROMOTION_RECONCILIATION_PROVIDER_SETTINGS_FILE=/ABSOLUTE/PROVIDER_SETTINGS
LIQUENT_STAGING_PROMOTION_RECONCILIATION_DATABASE_URL=DATABASE_URL
```

Invoke one bounded pass with the explicit process settings path:

```text
liquent-staging-promotion-reconcile /ABSOLUTE/PROCESS_SETTINGS
```

Interpret only the fixed result and exit status:

- `idle` on stdout with exit `0`: no eligible unknown attempt was present;
- `reconciled` on stdout with exit `0`: one exact durable reconciliation was
  completed;
- `unavailable` on stderr with exit `1`: stop and investigate outside this
  command; do not retry automatically;
- `invalid_invocation` on stderr with exit `2`: correct the invocation without
  assuming that reconciliation ran.

Never put either settings value, an operation identity, receipt, provider
response or database detail into command arguments beyond the single settings
path, logs, tickets or copied evidence. A second invocation is a new explicit
operator decision after current durable state has been reviewed.

## Required evidence

Record the release run, deployment run ID, previous and candidate digests,
backup snapshot ID, migration result, internal container health, external HTTPS
result, operator and decision. A first-ever staging deployment without a known
healthy previous digest is intentionally outside this automation and requires a
separate bootstrap procedure.
