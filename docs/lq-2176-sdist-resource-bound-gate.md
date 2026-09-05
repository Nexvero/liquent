# LQ-2176 sdist resource bound gate

- Compressed input is limited to 16 MiB.
- At most 4096 archive members are accepted.
- A member name is limited to 1024 UTF-8 bytes.
- One regular file is limited to 4 MiB.
- Aggregate regular payload is limited to 32 MiB.
- Non-file members must declare zero payload bytes.
- Every violation uses the existing detail-limited rejection.
