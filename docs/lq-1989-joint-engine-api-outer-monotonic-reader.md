# LQ-1989 Joint engine API outer monotonic reader

- One private reader owns outer monotonic access.
- The existing provider remains the clock source.
- Every provider result is immediately validated.
- Consumers receive only canonical float values.
- Provider exceptions retain existing handling.
- The reader exposes no clock detail.
- No dependency or signature changes.
