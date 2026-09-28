# LQ-1996 Detail-free joint engine API monotonic rejection

- Rejection reveals no malformed value.
- It reveals no failed read position.
- It reveals no provider implementation.
- Direct APIs expose only existing unavailable failure.
- CLI continues to expose status two only.
- No stderr diagnostic is added.
- No caller-controlled fallback exists.
