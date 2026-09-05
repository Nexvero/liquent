# LQ-1811 Joint engine API pre-finalization evidence gate contract

- Evidence shape is checked inside the operation body.
- Invalid shape prevents result construction.
- Success callback therefore receives no malformed handoff.
- Root final validation still executes on failure.
- Timing and terminal checks only process closed results.
- Raw verifier output never becomes public output.
- The command remains read-only.
