# LQ-2212 Wheel ZIP header gate

- The archive comment must be empty.
- Every member uses creator system 3 and version fields 20.
- ZIP64 and later extraction semantics are not accepted.
- Extra fields, member comments, and internal attributes fail closed.
- Existing external mode validation remains independently mandatory.
- Empty wheels fail before identity or content interpretation.
- Rejection uses the existing wheel verification boundary.
