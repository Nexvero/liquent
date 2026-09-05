# LQ-1441 Joint engine API one-shot source identity evidence

- Instrumented tests observe the same identity on both source loads.
- Acceptance-root identity is simultaneously preserved and checked.
- Bound verification succeeds only for the originally resolved source.
- Existing duplicate, timing, snapshot, and readback tests remain green.
- Standalone one-shot callers retain their prior behavior.
- No marker is accepted from an unbound replacement source.
- Evidence remains local and excludes external runtime attestation.
