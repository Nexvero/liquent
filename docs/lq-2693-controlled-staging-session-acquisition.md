# LQ-2693 — Controlled staging session acquisition

LQ-2693 composes the secret-free persistent registry with one injected session-
set acquirer. The exact active set and revision are resolved before acquisition
and resolved again after a complete validated handoff has been returned.

Initial absence prevents acquisition. Absence from the acquirer and revocation,
deactivation, replacement, or revision rotation during acquisition are neutral
absence. A substituted result or technical failure becomes one detail-free
unavailable signal. Thus an acquisition already in flight cannot override a
later system-of-record change.

The function accepts no user, workspace, role, membership, permission,
capability, provider claim, or allow boolean. It creates and persists no
credentials or sessions and adds no schema, migration, cache, retry, CLI,
deployment, or promotion. A concrete secret-backed acquirer, runtime handoff,
and promotion remain separate.
