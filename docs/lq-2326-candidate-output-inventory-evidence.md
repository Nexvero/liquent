# LQ-2326 Candidate output inventory evidence

- Focused tests prove a deterministic digest for the exact three-file inventory.
- They prove fail-closed rejection when an unexpected fourth entry is present.
- They prove fail-closed rejection when one required candidate file is absent.
- They prove fail-closed rejection when an expected name resolves to a symbolic
  link rather than a regular file.
- Production readiness remains false; publication and promotion remain separate.
