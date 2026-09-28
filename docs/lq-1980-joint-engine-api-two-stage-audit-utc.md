# LQ-1980 Joint engine API two-stage audit UTC

- Accepted audit reads initial validated UTC.
- Final validated UTC follows outer monotonic decision.
- Final value must not precede initial value.
- Retained snapshot is verified at final time.
- Registry audit performs no wall-clock read.
- Audit mode binding governs UTC access.
- Existing inner verifier timing remains unchanged.
