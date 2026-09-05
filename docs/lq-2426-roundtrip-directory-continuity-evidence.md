# LQ-2426 Roundtrip-directory continuity evidence

- Focused tests replace the roundtrip root with a fresh same-named directory.
- Explicit expected identity makes its otherwise valid one-file inventory fail closed.
- Source-order checks retain post-rebuild and post-verification identity checks.
- They retain shared-state binding and terminal inventory enforcement.
- Existing sdist parity and reproducible-wheel checks remain active.
- Production readiness remains false; publication and deployment remain forbidden.
