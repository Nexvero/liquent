# LQ-2401 Terminal roundtrip-artifact inventory gate

- The bundle phase requires the retained rebuilt-wheel path and its digest.
- It rejects any digest difference from the original distribution wheel.
- Directory identity and exact one-name inventory are checked before and after read.
- Stable name, size, and digest facts form a canonical roundtrip inventory digest.
- That digest is emitted in terminal bundle-gate facts.
