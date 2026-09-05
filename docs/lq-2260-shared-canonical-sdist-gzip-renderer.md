# LQ-2260 shared canonical sdist gzip renderer

- Normalization and verification use one deterministic gzip renderer.
- The renderer accepts only canonical TAR bytes and the requested epoch.
- It emits no filename, comment, extra field, or header checksum.
- Maximum compression fixes the Deflate strategy and XFL declaration.
- The neutral OS byte and standard CRC32/ISIZE trailer are deterministic.
- Rendering occurs in memory within the existing sdist size bounds.
- No filesystem extraction or additional artifact is introduced.
