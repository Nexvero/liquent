# LQ-1546 Joint engine API marker type owner evidence

- Tests replace regular-file state with directory state.
- Tests replace mode 0600 with permissive mode.
- Tests replace effective ownership with foreign ownership.
- Every forged observation fails closed.
- Authentic descriptor observations remain accepted.
- Existing read and record checks remain green.
- Evidence is local and deterministic.
