# LQ-1666 Joint engine API operation time audit

- LQ-1663 through LQ-1665 bound whole-operation duration.
- Inner timing alone no longer defines outer success.
- Registry and source rechecks lie inside the interval.
- Final topology validation immediately follows decision checks.
- Time failure remains unavailable and detail-free.
- No retry or marker deletion is introduced.
- Final freshness remains the next boundary.
