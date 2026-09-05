# LQ-1401 Joint engine API acceptance post-write evidence

- Tests observe one exact canonical value passed to readback.
- The durable marker bytes equal that expected value after success.
- Tests prove marker creation uses read-write descriptor access.
- Direct evidence rejects a hard-linked marker.
- Direct evidence rejects metadata mutation during readback.
- Existing atomic marker and root-binding tests remain green.
- Focused verification treats deprecation warnings as failures.
