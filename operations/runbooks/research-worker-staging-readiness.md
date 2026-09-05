# Research worker staging-readiness evidence

This checklist is a fail-closed approval gate for one isolated staging
deployment. It does not deploy, migrate, create identities or jobs, read a
Production secret, or declare Production readiness.

## Bound run

Record one opaque run ID, UTC start time, staging environment identity,
operator identity, reviewer identity, repository revision, immutable
application image digest, Compose file SHA-256, and expected migration head.

Every item below must refer to that same run and digest. Reused evidence,
mutable image tags, omitted values, or evidence from another environment make
the outcome `unavailable`.

## Preconditions

- [ ] The application image is referenced as `repository@sha256:<64 lowercase hex>`.
- [ ] The image revision and retained release manifest bind that exact digest.
- [ ] `liquent-research-worker` exists in the image and resolves without PATH mutation.
- [ ] The image reports runtime UID and GID `10001:10001`.
- [ ] The staging PostgreSQL database is disposable and contains no Production data.
- [ ] Backup/restore and rollback evidence for the same staging revision is current.
- [ ] Trading connectivity is `disabled` and no broker or exchange secret is present.

## Compose render

- [ ] Render with the reviewed Compose file and explicit real `runtime.env` and image environment sources.
- [ ] Rendering succeeds with no unresolved interpolation or mutable image reference.
- [ ] The worker command has only `--configuration` and `--database-url-file` inputs.
- [ ] The worker has no published port and no attachment to `liquent_public`.
- [ ] Research data, worker configuration, and worker ID mounts are read-only.
- [ ] Only the named artifact volume is writable by the worker.
- [ ] The database URL is mounted at `/run/secrets/database_url`, never rendered as a value.
- [ ] The rendered service retains `stop_grace_period: 60s` and concurrency one.

Retain the rendered configuration only after redacting host paths. Never retain
environment files, DSNs, secret contents, or raw mount-source locations.

## Runtime ownership inspection

Before worker startup, inspect from the exact image/runtime-user boundary:

- [ ] Configuration and worker-ID inputs are regular files, link count one,
      owned by UID `10001`, and mode `0400` or `0600`.
- [ ] The database-URL file is regular, link count one, owned by UID `10001`,
      and mode `0400` or `0600` as observed inside the container.
- [ ] Research-data root is readable but not writable by UID `10001`.
- [ ] Artifact root is a real directory owned by UID `10001`, not group/world
      writable, and supports create, fsync, hard-link, read-back, and removal
      of a staging-only probe beneath a dedicated temporary prefix.

Do not infer effective ownership from Compose source text. Some runtimes may
implement file-backed secret metadata differently; only in-container evidence
for this exact runtime is acceptable. Remove only the dedicated probe created
by this checklist.

## Migration and startup

- [ ] Start the migration gate before the worker and retain its exit code zero.
- [ ] An independent read-only query observes the exact expected Alembic head.
- [ ] Start exactly one worker instance from the bound image and rendered config.
- [ ] The worker remains running through at least one bounded idle interval.
- [ ] No claim, outcome, artifact, identity, membership, or permission is
      created merely by startup or an empty queue.
- [ ] Logs contain no DSN, credential, host path, user, workspace, job, claim,
      snapshot, artifact content, or exception detail.

## Controlled job proof

- [ ] Admit one staging-only research job through the existing authenticated,
      CSRF-protected, currently authorized Control Plane.
- [ ] Observe exactly one claim and at least one initial heartbeat.
- [ ] Observe one terminal outcome and no second claim for the same job.
- [ ] Verify the immutable artifact bytes against the persisted lowercase
      SHA-256 without recording the private artifact content.
- [ ] Revoke `research:write`, submit a second staging-only job before claim,
      and observe fail-closed invalidation without resolver or artifact access.

Use only synthetic non-sensitive CSV data. This is backtesting evidence, not a
profitability test or permission for live or paper trading.

## SIGTERM proof

- [ ] With the queue idle, send exactly one SIGTERM to the worker container.
- [ ] Observe no later claim, normal process exit, and shutdown within 60 seconds.
- [ ] Restart the same bound image and verify exact migration readiness again.
- [ ] While one staging-only job is running, send exactly one SIGTERM and
      observe either claim-bound terminal completion within the grace period or
      later lease-based recovery; never duplicate terminal outcomes.
- [ ] Confirm no SIGKILL was needed for the approved path.

## Detail-free decision

Record only `approved`, `rejected`, or `unavailable` outside the restricted
evidence record. Missing, stale, mismatched, inaccessible, secret-bearing, or
ambiguous evidence is `unavailable`; an explicit failed invariant is
`rejected`. Neither result identifies the failing secret, path, job, actor, or
infrastructure detail.

Approval applies only to the bound staging run and image digest. It does not
approve Production, another digest, another Compose render, scaling above one,
automatic deployment, or creation of regular users, workspaces, memberships,
capabilities, or jobs.
