# LQ-1679 Joint engine API completion time contract

- Final clock capture follows post-verification source observation.
- Total duration therefore includes convergence work.
- Completion UTC may not precede verification UTC.
- Completion monotonic may not precede operation start.
- Complete interval remains limited to 30 seconds.
- Caller cannot supply completion time.
- Invalid ordering fails unavailable.
