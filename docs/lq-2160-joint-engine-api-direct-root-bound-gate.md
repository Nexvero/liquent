# LQ-2160 Joint engine API direct root bound gate

- Direct rendered root is bounded to 4095 bytes.
- Every rendered component is bounded to 255 bytes.
- Oversized direct roots stop before clocks.
- Oversized direct roots stop before descriptors.
- No truncation or hashing occurs.
- CLI and direct limits are identical.
- No caller override exists.
