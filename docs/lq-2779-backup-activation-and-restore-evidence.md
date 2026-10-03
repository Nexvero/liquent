# LQ-2779: Backup activation and restore evidence

## Released artifact

Controlled backup release run `37051548122` published version `0.1.4` from
verified `main` commit
`f554cbd5d39bc8c66b209148485c2b4b10dd8422` as:

`ghcr.io/nexvero/liquent-backup@sha256:843a7c81dcd699eb2ae475b92912885d595cf085278a6771d5218dc5a1741658`

The run produced attestation `52258601` and release artifact
`liquent-backup-release-0.1.4-f554cbd5d39bc8c66b209148485c2b4b10dd8422`
with artifact digest
`sha256:a92ae8ad4d2cfcbeeda089598c074f56ace4c46eed0f8e578cbed83ca7f4c0be`.
The unchanged Grype gate reported zero High findings, zero Critical findings
and zero fixable High/Critical findings.

## Production activation

The production backup configuration already bound the OVH S3-compatible
repository to region `eu-west-par`. The new image was pulled by immutable
digest and independently checked for runtime identity `10001:10001`, source
revision and configuration validity before activation.

The owner-only image environment was replaced atomically and remains mode
`0600`. The previous `0.1.3` digest was retained in an owner-only rollback copy
until the first scheduled `0.1.4` run succeeded.

One explicit backup run using the activated digest created encrypted snapshot
`ca346edb`. The repository metadata check completed without errors. No manual
retention or snapshot deletion was executed. Both backup timers remained
active and no one-shot backup container remained after completion.

## Isolated restore acceptance

Snapshot `ca346edb` was restored into a new disposable path without mounting a
Production database or Production PostgreSQL volume. The restored custom dump
was 500982 bytes. Its manifest recorded migration head `20260916_0046` and
database SHA-256
`4a989fa875b1a660b5325d89f34c579a75143949bb0086d8f24a598e748f8035`.
The restore operator verified both that checksum and the `pg_restore` catalog.

The dump imported successfully into a disposable PostgreSQL container backed
by a new disposable volume. The restored database contained 159 public tables
and reported migration head `20260916_0046`.

The matching application image
`ghcr.io/nexvero/liquent@sha256:c17271bc000f4a7d65d5b67fafac743d6028c719dc7b3f1736282b4106240f92`
started against that database in an internal Docker network with no published
ports. Liveness and readiness both returned HTTP 200. The application and
database containers, internal network, disposable volume, restored files and
test-only secrets were removed after acceptance.

## Scheduled-run confirmation and cleanup

The first timer-triggered backup using `0.1.4` started at
`2026-10-03T02:23:58Z` and completed successfully at
`2026-10-03T02:24:09Z`. The service returned result `success` and exit status
zero while still using the approved immutable digest. It created snapshot
`2997744f`, applied the configured retention policy and completed the
repository metadata check with no errors. Both backup timers remained active.

After that evidence was captured, the superseded owner-only rollback copy
`backup-images.env.pre-0.1.4` was removed. No snapshot, repository evidence,
active image configuration or Production data was removed. The temporary
read-only follow-up automation was paused after its one-time purpose was
fulfilled.
