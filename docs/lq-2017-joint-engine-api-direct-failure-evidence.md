# LQ-2017 Joint engine API direct failure evidence

- Tests cover Accept and both Audit modes.
- Multiple ordinary exception classes normalize.
- Existing unavailable instances are preserved.
- Interrupt and process exit propagate.
- Late Accept failure preserves durable marker.
- Valid direct operations still return None.
- Strict warnings remain enabled.
