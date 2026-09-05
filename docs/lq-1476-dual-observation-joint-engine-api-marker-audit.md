# LQ-1476 Dual-observation joint engine API marker audit

- Accepted-source audit observes the marker before verification.
- It observes the marker again after source revalidation.
- Full immutable observation equality is required for success.
- Both observations retain expected registry-root binding.
- Cryptographic, source, time, and duration checks remain unchanged.
- Neutral absence at either phase fails the accepted-source audit.
- The CLI and operation mode surface remain unchanged.
