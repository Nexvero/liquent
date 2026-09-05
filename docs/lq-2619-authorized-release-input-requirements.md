# LQ-2619 Authorized release-input requirements

- Repository action requires the accepted full candidate commit and explicit destination authority.
- Signing requires current signer identity, approved key authority, candidate commit, and exact image digest.
- Promotion requires the retained signature, immutable source reference, and approved registry destination.
- Publication requires current provider ownership, scoped credential authority, TLS/DNS readiness, and approved target.
- Staging requires an authorized environment, protected DSN delivery, backup policy, migration window, and rollback owner.
- Deployment requires the accepted staging evidence, immutable digest, change window, health criteria, and rollback approval.
- Inputs are resolved from their authoritative systems and are never replaced by caller-supplied allow flags.
- Expired, revoked, ambiguous, cross-environment, or identity-mismatched input is rejected before side effects.
- Logs and receipts expose decision facts without exposing secret values or sensitive connection detail.
- This slice invents no authority, credential, environment, target, or approval.
