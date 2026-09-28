# LQ-1369 Joint engine API single operation wrapper evidence

- Direct wrapper tests cover success and failure finalization.
- Accept failure proves final validation still executes once.
- Registry-audit failure proves the same behavior.
- Accepted-source-audit failure proves the same behavior.
- Existing successful accept and both audit flows remain green.
- CLI failure remains the closed numeric status without inner detail.
- Architecture guardrails remain in focused verification.
