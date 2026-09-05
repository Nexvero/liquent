# LQ-1691 Joint engine API terminal duration contract

- Terminal monotonic time follows fourth source observation.
- It may not precede completion monotonic time.
- It may not exceed 30 seconds from operation start.
- Convergence work is therefore inside the duration bound.
- Wall time remains unnecessary for this elapsed check.
- Caller cannot provide a terminal clock value.
- Invalid duration fails unavailable.
