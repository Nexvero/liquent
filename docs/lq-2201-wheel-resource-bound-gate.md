# LQ-2201 Wheel resource bound gate

- Compressed wheel input is limited to 16 MiB.
- At most 2048 members are accepted.
- One member name is limited to 512 UTF-8 bytes.
- One uncompressed file is limited to 4 MiB.
- Aggregate uncompressed payload is limited to 32 MiB.
- SHA-256 is streamed instead of loading the archive again in full.
- Every violation uses the existing verifier rejection boundary.
