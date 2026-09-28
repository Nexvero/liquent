# LQ-1585 Joint engine API acceptance delta evidence

- Tests observe bound registry inspection before and after accept.
- Exact single canonical marker addition succeeds.
- Missing marker after a stubbed inner operation is rejected.
- Unrelated file addition is rejected by final inspection.
- Existing state and identity tests remain green.
- No marker detail is exposed by failure.
- Evidence is local and deterministic.
