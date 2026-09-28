# LQ-1711 Joint engine API outer audit duration contract

- Every operation audit owns one outer monotonic interval.
- It begins before initial operation-root resolution.
- It ends after evidence rechecks succeed.
- The interval may not exceed 30 seconds.
- Monotonic time may not move backward.
- Caller duration is never accepted.
- Invalid timing fails detail-free.
