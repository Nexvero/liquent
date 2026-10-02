# LQ-2777: Backup release handoff

## Released artifact

Pull request `#285` was squash-merged into `main` as commit
`30d83187fa285cf2b443768abf97387cf5c1162e`. Main quality run `36965315794`
completed successfully before publication.

Controlled backup release run `36968066698` published version `0.1.3` as:

`ghcr.io/nexvero/liquent-backup@sha256:07387c4cecbb787864f2d91c2d5336327daa3e6a5c21809558002b73831f5f54`

The immutable tag used during publication was
`0.1.3-30d83187fa285cf2b443768abf97387cf5c1162e`.

## Acceptance evidence

The controlled workflow built the image from the verified commit, ran the
hardened backup smoke test, generated the SPDX SBOM and passed the unchanged
Grype gate with `--fail-on high --only-fixed`. Authentication to GHCR occurred
only after those gates passed. GitHub attestation `52052200` was created for the
published digest.

The uploaded release evidence artifact is
`liquent-backup-release-0.1.3-30d83187fa285cf2b443768abf97387cf5c1162e`
with artifact digest
`sha256:67b042c0c4f194dff896c52f3cc12e804d2998ad4d346ed31ae1f8c283f98d3c`.

An earlier run, `36965348348`, stopped before build and publication because the
required successful main-push quality run had not completed. It published no
image.

## Operational boundary

This handoff authorizes the immutable image as an eligible input to the
opt-in backup overlay. It does not create the private object-storage bucket,
credentials, Restic repository or password; install host secrets; enable the
systemd timers; execute a backup or restore; or authorize deployment. Those
steps remain subject to the activation gate in
`operations/runbooks/backup-restore.md`.
