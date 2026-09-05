# LQ-1345 Joint engine API operation child identity evidence

- Tests replace `source-set` after initial child identity capture.
- Tests separately replace `accepted-runs` at the same failure window.
- Replacement copies the original directory content and private mode.
- Final descriptor-relative identity comparison rejects both cases.
- Existing missing, extra, mode, and symlink child tests remain green.
- Operation acceptance and audit composition tests remain green.
- Focused evidence executes under strict warning handling.
