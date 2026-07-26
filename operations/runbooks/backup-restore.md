# Backup and restore runbook

## Backup activation gate

Do not schedule backups until all items are recorded in the deployment log:

1. private OVHcloud S3-compatible bucket created in the approved region,
2. dedicated least-privilege object-storage identity created,
3. Restic repository initialized with a separately protected password,
4. secret files installed with owner-only permissions,
5. `backup.sh --check` succeeds in the final image,
6. first backup succeeds and its snapshot ID is recorded,
7. alert owner and maximum acceptable backup age are configured.

Never paste credentials, repository passwords, database passwords, or `.pgpass`
content into tickets, logs, shell history, or this repository.

## Daily backup

The scheduled job creates a custom-format PostgreSQL dump, records its SHA-256
and migration head, and sends the dump plus immutable artifacts to one encrypted
Restic snapshot. A metadata-level `restic check` must pass before the job is
reported successful.

Retention is not implicit. Run `retention.sh --apply` from a reviewed scheduled
job after a successful backup. Policy: 7 daily, 4 weekly, and 6 monthly
snapshots. Review the forget plan and repository size before policy changes.

## Isolated restore test

1. Declare incident/test owner, snapshot, start time, and recovery environment.
2. Create an isolated host or disposable volumes with no Production mounts.
3. Run `restore-verify.sh --target /recovery/<test-id>`; the target must not exist.
4. Confirm dump checksum and `pg_restore --list` validation.
5. Create an empty recovery PostgreSQL instance of the approved major version.
6. Import the dump into that instance; never into Production during a test.
7. Apply no newer migration until the restored release has been identified.
8. Start the matching application artifact with network egress disabled.
9. Verify readiness, schema revision, artifact references, permissions, and
   documented functional samples.
10. Record RPO, RTO, snapshot ID, release digest, deviations, and final result.
11. Destroy or securely sanitize the isolated recovery environment.

## Production recovery

Production recovery requires explicit incident authorization. Stop writes,
preserve the failed state for diagnosis when possible, select the recovery
point, and rehearse commands against an isolated target first. Application
rollback does not imply schema downgrade. Reopen traffic only after migration
revision, readiness, data sampling, permissions, and audit continuity pass.

## Failure handling

- Backup failed: preserve logs without secrets, do not prune, retry only after
  cause classification, alert when the last successful snapshot exceeds 24 h.
- Repository check failed: stop retention/prune, treat repository as suspect,
  preserve evidence, and follow Restic recovery guidance.
- Restore checksum/catalog failed: do not import; try a previous snapshot and
  open an incident.
- Lost Restic password: snapshots are unrecoverable; password custody therefore
  needs a separate verified recovery mechanism before go-live.
