# LQ-1837 Joint engine API mode result binding evidence

- Tests reject five non-boolean mode values.
- Tests inject a valid accepted result into registry mode.
- Tests inject a valid registry result into accepted mode.
- Both cross-mode handoffs fail closed.
- Exact false and true modes still complete.
- Existing mode-specific audit tests remain green.
- All focused warnings are treated as errors.
