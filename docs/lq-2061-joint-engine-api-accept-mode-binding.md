# LQ-2061 Joint engine API accept mode binding

- Accept-once maps only to Accept.
- It does not call either Audit mode.
- Parsed root passes unchanged.
- Accept is invoked exactly once.
- Result must be exactly None.
- No caller boolean controls this route.
- No fallback route exists.
