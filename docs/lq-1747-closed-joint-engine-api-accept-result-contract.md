# LQ-1747 Closed joint engine API accept result contract

- Accept handoff uses one closed immutable result type.
- Raw source and registry tuples are no longer dispatched.
- Construction validates complete result semantics.
- Invalid results fail before success finalization.
- Representation discloses no source or marker detail.
- Public accept-once still returns no value.
- Failure remains detail-free.
