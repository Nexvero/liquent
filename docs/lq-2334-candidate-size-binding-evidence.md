# LQ-2334 Candidate size-binding evidence

- Focused tests prove valid candidates retain deterministic inventory identity.
- They prove fail-closed rejection when an expected size differs from the opened
  candidate file size.
- A source-boundary assertion proves size rejection precedes the hashing loop.
- Existing topology, mode, hardlink, identity, and digest tests remain active.
- Production readiness remains false; publication and promotion remain separate.
