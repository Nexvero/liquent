# LQ-1480 Joint engine API operation marker stability

- Existing operation audit composition invokes dual marker observation.
- It passes the resolved acceptance identity unchanged to both reads.
- Inner observation detects marker replacement within a stable registry.
- Outer final validation independently detects child-root replacement.
- Source, registry, and marker identities remain distinct evidence.
- No caller role, allow flag, or identity override is accepted.
- Technical failure details do not cross the command boundary.
