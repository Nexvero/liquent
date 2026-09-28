# LQ-2595 Local container smoke and Grype gate evidence

- The patched local image is `sha256:f13074fb...ad488`.
- Runtime user is exactly `10001:10001` and the healthcheck is present.
- The revision label retains source commit `83699b15...78236`.
- The repository hardened container smoke test passed.
- Grype used `.grype.yaml`, `only-fixed`, and failure cutoff High.
- The patched scan reported zero fixable High or Critical blockers.
- JSON scan output remains private temporary local evidence.
- The image derives from an uncommitted tree and is not a release candidate.
- No push, signature, publication, staging, or deployment occurred.
