# LQ-2005 Joint engine API clock failure evidence

- Tests cover all three outer readers.
- Value, OS, and runtime failures normalize.
- Existing unavailable instances are preserved.
- Cause suppression is explicit.
- Interrupt and process exit propagate.
- Valid UTC and monotonic values remain unchanged.
- Strict warnings remain enabled.
