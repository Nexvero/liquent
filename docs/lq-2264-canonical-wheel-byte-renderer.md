# LQ-2264 canonical wheel byte renderer

- The verifier renders one ZIP from validated member records and payloads.
- It preserves validated order, timestamps, modes, flags, and ZIP versions.
- Every member uses the required Deflate compression method.
- Archive and member comments and extra fields remain absent.
- Rendering occurs only after bounded member reads have succeeded.
- The renderer operates in memory and extracts no filesystem content.
- Existing source and RECORD bindings remain independent checks.
