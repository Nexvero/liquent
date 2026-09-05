# LQ-1719 Ordered joint engine API outer audit contract

- Outer start clocks precede initial root resolution.
- Inner audit verification executes next.
- Second root resolution and evidence rechecks follow.
- Outer monotonic finish then bounds elapsed work.
- Accepted final UTC and freshness verification follow.
- Exact root validation closes the operation.
- Every stage remains fail-closed.
