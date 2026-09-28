# LQ-2580 Parent-child identity-separation evidence

- Focused evidence uses the real workspace tuple as an expected child tuple.
- The structurally valid alias is rejected before workspace opening.
- Existing malformed, duplicate, snapshot, descriptor, and topology tests remain.
- The caller observes only controlled preflight rejection.
- Complete project regression and diff hygiene are required for handoff.
- Production readiness remains false; publication and deployment stay forbidden.
