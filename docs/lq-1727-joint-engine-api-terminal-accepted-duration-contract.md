# LQ-1727 Joint engine API terminal accepted duration contract

- Terminal monotonic time follows accepted evidence rereads.
- It may not precede outer final monotonic time.
- Start-to-terminal duration may not exceed 30 seconds.
- Source and marker convergence are inside the bound.
- UTC remains the freshness authority only.
- Caller terminal time is never accepted.
- Invalid timing fails unavailable.
