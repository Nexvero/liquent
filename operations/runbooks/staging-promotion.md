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

### Install reconciliation settings

Before the first reconciliation invocation, prepare the provider and process
source files in a separate owner-held directory. Both source files must be
regular files owned by the effective installer user, have mode `0600`, exactly
one hard link, UTF-8 content and a trailing newline. Prepare two distinct
absolute target paths in existing owner-held directories that are not writable
by group or others. The process source must name the exact provider target.

Install the pair once with four explicit absolute paths in this fixed order:

```text
liquent-staging-promotion-reconciliation-settings-install /ABSOLUTE/PROVIDER_SOURCE /ABSOLUTE/PROVIDER_TARGET /ABSOLUTE/PROCESS_SOURCE /ABSOLUTE/PROCESS_TARGET
```

Interpret only the fixed installation result and exit status:

- `installed` on stdout with exit `0`: both targets were durably published;
- `present` on stderr with exit `3`: stop; at least one target was already
  present and no existing content was compared or replaced;
- `unavailable` on stderr with exit `1`: stop and investigate outside this
  command; do not retry automatically;
- `invalid_invocation` on stderr with exit `2`: correct the invocation without
  assuming that either target was installed.

Never place either settings value in command arguments, logs, tickets or copied
evidence. Do not remove or overwrite a retained provider target after a failed
activation. Any cleanup, rotation or replacement requires a separate reviewed
operator procedure. Installation does not authorize reconciliation; review the
durable unknown-effect state and make a new explicit operator decision before
the bounded reconciliation command below.

### Audit reconciliation readiness

After a successful settings installation, audit only the closed settings and
database prerequisites. Pass the explicit absolute process target path; do not
copy either settings value into the command:

```text
liquent-staging-promotion-reconciliation-readiness-audit /ABSOLUTE/PROCESS_SETTINGS
```

Interpret only the fixed audit result and exit status:

- `ready` on stdout with exit `0`: the settings projections and database schema
  were ready at audit time; continue only to a separate review of current
  durable state and an explicit operator decision;
- `unavailable` on stderr with exit `1`: stop and investigate outside this
  command; do not retry automatically and do not invoke reconciliation;
- `invalid_invocation` on stderr with exit `2`: correct the path argument
  without assuming that readiness was checked.

The audit makes no provider request, performs no reconciliation or database
mutation, and grants no promotion or deployment authority. A `ready` result can
become stale immediately and is prerequisite evidence only. Never record the
settings paths, values, endpoint, database URL or technical failure detail in
logs, tickets or copied evidence.

### Audit an eligible reconciliation candidate

After a fresh `ready` result, inspect only whether the durable journal currently
contains an eligible unknown-effect candidate. Pass the same explicit absolute
process settings path:

```text
liquent-staging-promotion-reconciliation-candidate-audit /ABSOLUTE/PROCESS_SETTINGS
```

Interpret only the fixed audit result and exit status:

- `pending` on stdout with exit `0`: at least one eligible candidate existed at
  audit time; make a new explicit operator decision before reconciliation;
- `idle` on stdout with exit `0`: no eligible candidate existed at audit time;
  stop without invoking reconciliation;
- `unavailable` on stderr with exit `1`: stop and investigate outside this
  command; do not retry automatically and do not invoke reconciliation;
- `invalid_invocation` on stderr with exit `2`: correct the path argument
  without assuming that durable state was inspected.

The audit validates the closed settings and database readiness, then reads the
bounded unknown-effect index exactly once. It makes no provider request,
performs no reconciliation or database mutation, and never exposes an operation
identity. A `pending` result can become stale immediately, is prerequisite
evidence only, and grants no reconciliation, promotion or deployment authority.
Never record settings paths or values, endpoint, database URL, operation
identity or technical failure detail in logs, tickets or copied evidence.

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

- `idle` on stdout with exit `0`: no durable reconciliation was recorded by
  this bounded pass; this does not prove that no eligible candidate exists,
  because a provider may still report the selected operation as pending;
- `reconciled` on stdout with exit `0`: one exact durable reconciliation was
  completed;
- `unavailable` on stderr with exit `1`: stop and investigate outside this
  command; do not retry automatically;
- `invalid_invocation` on stderr with exit `2`: correct the invocation without
  assuming that reconciliation ran.

Never put either settings value, an operation identity, receipt, provider
response or database detail into command arguments beyond the single settings
path, logs, tickets or copied evidence. A second invocation is a new explicit
operator decision after current durable state has been reviewed. If the result
is `idle`, use a new candidate audit only as fresh read-only evidence; do not
convert either result into automatic retry authority.

## Required evidence

Record the release run, deployment run ID, previous and candidate digests,
backup snapshot ID, migration result, internal container health, external HTTPS
result, operator and decision. A first-ever staging deployment without a known
healthy previous digest is intentionally outside this automation and requires a
separate bootstrap procedure.

## Reconciliation exercise authorization handoff

Before using the reconciliation commands against the real staging environment,
review the decision packet in
`docs/lq-2761-staging-reconciliation-exercise-authorization-handoff.md`. The
packet must establish the exact staging boundary, owner-private settings
custody, current provider authorization, current PostgreSQL readiness, current
durable candidate state, named decision roles and a bounded exercise window.

The packet itself is not authorization and must contain no settings path or
value, endpoint, database URL, credential, operation identity, provider
response, receipt or technical error detail. A separate approver records only
`approved`, `rejected` or `expired`. Approval is valid for one bounded exercise
window and cannot be reused.

Within an approved window, retain the existing manual order: settings
installation, readiness audit, candidate audit and one reconciliation pass.
Treat every fixed command result as a new stop boundary. Missing, stale,
ambiguous, rejected or expired evidence stops the exercise. A later invocation
requires fresh evidence and a new explicit decision; there is no automatic
retry, polling, bulk drain, promotion or deployment authority.

Record that decision with the fixed, data-minimizing packet in
`docs/lq-2762-staging-reconciliation-exercise-decision-packet.md`. Complete
every confirmation and UTC timestamp immediately before the bounded exercise.
Only an unexpired `approved` packet with every confirmation set to `yes` may be
consulted for that one window. The packet contains no path, settings value,
endpoint, database detail, operation identity, person or account. It is not a
credential and cannot be reused for a retry or later pass.

Validate the completed packet once with
`docs/lq-2763-staging-reconciliation-exercise-decision-packet-validation.md`
before consulting any command step. Check its exact shape and tokens, current
UTC window, unchanged prerequisite evidence, role separation and single-use
state in that order. Record only `valid`, `rejected`, `expired` or `invalid`
without packet values or technical detail. A `valid` result is point-in-time
evidence, not command authority. Every other, missing or ambiguous result stops
before settings installation, provider access or reconciliation.

After the bounded exercise stops, complete the fixed outcome packet in
`docs/lq-2764-staging-reconciliation-exercise-outcome-packet.md`. Record the
fixed result of every invoked command and `not_run` for each later command that
the first stop boundary prevented. Verify the final candidate state
independently through the system of record; use only `reconciled`, `present` or
`unverified` and never copy an operation identity or technical detail.

Close the exercise window and consume the decision packet even when the run
stopped early. The outcome packet grants no authority for another pass, retry,
polling, promotion or deployment. A later exercise starts again with fresh
evidence, a new decision packet, a separate decision and a new validation.

Validate the completed outcome packet once with
`docs/lq-2765-staging-reconciliation-exercise-outcome-packet-validation.md`.
Check its exact shape and tokens, command stop sequence, independent durable
evidence, result consistency and closure in that order. Do not repair the
packet or re-run a command to make validation pass.

Record only `valid`, `invalid` or `unverified`, without packet values or
technical detail. A `valid` result is immutable completion evidence for the
already-finished bounded window and does not authorize another exercise,
retry, polling, promotion or deployment. Every other, missing or ambiguous
result remains closed and requires investigation outside this command chain.
