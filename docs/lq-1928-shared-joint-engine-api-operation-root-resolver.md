# LQ-1928 Shared joint engine API operation root resolver

- One helper composes root resolution and exact type validation.
- It returns only canonical operation-roots values.
- Raw resolver output never reaches operation logic.
- Existing resolver remains filesystem authority.
- No fallback unvalidated root resolution is available.
- Value invariants remain enforced by root model.
- No new port or persistence model is introduced.
