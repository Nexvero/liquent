# LQ-2617 Repository-review acceptance checklist

- Review starts from the exact merge base and the complete integration-branch diff.
- Every commit must have a bounded purpose and preserve the documented runtime-evidence boundary.
- Review confirms no unresolved conflict marker, unexpected symlink, oversized file, or untriaged secret-like material.
- Migration history remains linear at `20260826_0042` and the release inventory remains internally consistent.
- Wheel, source distribution, container, and installed entry-point scope must agree for the selected candidate.
- Normal, PostgreSQL, preflight, image-smoke, and vulnerability evidence must be attributed separately and accurately.
- A reviewer records acceptance or rejection against an immutable full commit identifier.
- Silence, branch visibility, test success, or local readiness is not repository acceptance.
- Any post-review code change requires a new diff review and applicable renewed evidence.
- This checklist records no review decision and grants no repository mutation authority.
