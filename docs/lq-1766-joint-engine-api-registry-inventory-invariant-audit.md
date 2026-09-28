# LQ-1766 Joint engine API registry inventory invariant audit

- Registry results now expose one canonical evidence inventory.
- Each accepted run has at most one result observation.
- Each marker generation and state is independently unique.
- Acceptance values remain exactly evidence-derived.
- Corrupt result construction fails before publication.
- Persistent marker semantics are not broadened.
- Registry inventory closure is complete for this slice.
