# LQ-1851 Joint engine API accept handoff failure contract

- Invalid return type uses existing unavailable failure.
- No Python attribute or unpacking error escapes.
- Returned object details never enter failure text.
- Failure does not erase a potentially durable marker.
- Operation-root validation still closes the attempt.
- CLI status mapping remains unchanged.
- No new exception name is introduced.
