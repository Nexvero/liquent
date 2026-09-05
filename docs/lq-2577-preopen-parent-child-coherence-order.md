# LQ-2577 Preopen parent-child coherence order

- Identity shape, fixed names, child uniqueness, and parent exclusion run first.
- Workspace opening occurs only after all coherence checks succeed together.
- One aliased child prevents inspection of otherwise valid expected entries.
- No partial descriptor set is created on this rejection path.
- Failure remains the existing detail-limited controlled rejection.
- Later invocations must present a complete newly valid snapshot.
