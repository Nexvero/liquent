# LQ-2608 External release-authority blocker matrix

- Real signing requires an approved current signer authority and protected private-key access.
- Promotion requires a matching current registry projection and retained detached signature.
- Publication requires approved provider ownership, target, credential scope, TLS/DNS, and egress evidence.
- The publication host requires four matching independent reviewer attestations.
- Registry upload requires explicit supervised invocation and immutable provider read-back.
- Staging acceptance requires an authorized environment-specific evidence run.
- Deployment requires its own digest, migration, backup, health, and rollback approval.
- None of these authorities can be inferred from local tests, a Git branch, or image availability.
- Missing, expired, revoked, mismatched, or unavailable evidence fails closed before provider contact.
- The next progress point requires externally supplied authority; local preparation is complete.
