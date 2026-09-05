# LQ-2524 Close-failure detail normalization

- Any child or workspace close error becomes controlled preflight rejection.
- The public message remains the existing fixed detail-limited text.
- Raw error text, errno, descriptor value, and child name are not returned.
- A cleanup failure cannot turn an earlier rejection into apparent success.
- Successful verification is reported only after all close attempts succeed.
- No new exception type or externally observable status is added.
