# LQ-2616 Release residual-risk and stop criteria

- Local evidence cannot prove current remote branch state, signer authority, registry policy, provider ownership, or staging health.
- The retained Grype result has one Medium finding and zero High or Critical findings; later database updates may change that assessment.
- Temporary local receipts and scan output are not durable provenance and must not be treated as an external audit store.
- Candidate, source tree, image digest, signature, registry read-back, and environment must remain mutually bound.
- Drift in any binding, migration head, dependency lock, base image, or release-control inventory requires renewed applicable checks.
- Unexpected remote ancestry, unreviewed commits, dirty inputs, unavailable evidence, or ambiguous authority stops release progression.
- Failed migration rehearsal, health checks, smoke checks, or rollback readiness stops staging acceptance or deployment.
- Detail-free technical failure must not be converted into authorization or a retry that bypasses a consumed gate.
- Residual acceptance belongs to named external reviewers and operators, not to local test success.
- Production readiness remains false until every externally owned gate succeeds for the same immutable candidate.
