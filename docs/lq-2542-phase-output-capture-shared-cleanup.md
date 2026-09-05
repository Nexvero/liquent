# LQ-2542 Phase-output capture shared cleanup

- Phase-output capture delegates child and workspace closes to the shared helper.
- Both descriptors are supplied only when their opens succeeded.
- The child remains ordered before the parent workspace anchor.
- Cleanup executes after success, rejection, and operating-system failure alike.
- A cleanup failure overrides a pending identity result with rejection.
- No captured identity escapes before cleanup has succeeded.
