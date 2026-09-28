# LQ-1406 Joint engine API untrusted marker cleanup audit

- Failed post-write verification cannot leave a trusted marker result.
- Cleanup remains narrow to a marker created by the current call.
- The trust transition occurs only after exact readback succeeds.
- Durable directory synchronization remains required after success.
- Existing one-shot duplicate and failure-window semantics remain intact.
- Focused cleanup and acceptance regression evidence passes.
- No general deletion capability is introduced.
