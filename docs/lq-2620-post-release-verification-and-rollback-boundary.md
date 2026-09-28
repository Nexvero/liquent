# LQ-2620 Post-release verification and rollback boundary

- Post-release verification reads the deployed immutable digest and compares it with the approved candidate binding.
- Migration head, service health, dependency reachability, and bounded smoke behavior are checked independently.
- Verification must not mutate identity, membership, capability, trust, or research data as a side effect.
- Missing or detail-free unavailable observations remain failure, not inferred health.
- Acceptance requires all mandatory observations within the approved window and environment.
- A failed mandatory observation invokes the preapproved stop or rollback decision path.
- Rollback uses an approved immutable predecessor and its compatible database-restoration plan.
- Rollback success requires renewed digest, migration, health, and smoke verification.
- Incident evidence preserves timestamps and identity bindings while excluding secrets and sensitive payloads.
- Deployment success never erases failed checks or authorizes unrelated follow-up mutation.
- This slice performs no environment probe, deployment, rollback, or incident action.
