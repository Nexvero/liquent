# LQ-2071 Joint engine API CLI namespace handoff contract

- Parser handoff must be exact Namespace.
- Handoff contains exactly two fields.
- Operation root field must be Path.
- Mode field must be an allowed exact string.
- Extra and missing fields fail closed.
- Validation precedes dispatch.
- Public CLI syntax remains unchanged.
