# LQ-2615 External release-execution sequence

- First, repository reviewers accept an exact immutable candidate and its complete merge diff.
- Second, the release authority verifies that candidate against matching preflight and image evidence.
- Third, an approved signer binds the immutable candidate and image digest to a retained signature.
- Fourth, promotion verifies the signature and immutable registry target before any upload.
- Fifth, provider publication uses current scoped credentials and confirms immutable read-back.
- Sixth, staging runs environment-specific migrations, health checks, smoke checks, and acceptance gates.
- Seventh, deployment requires a separately approved digest, backup, migration, health, and rollback plan.
- A failed, absent, expired, revoked, or mismatched gate stops the sequence before the next side effect.
- No later success retroactively authorizes or repairs an earlier missing gate.
- This slice performs none of the external actions in the sequence.
