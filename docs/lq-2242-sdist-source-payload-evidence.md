# LQ-2242 sdist source-payload evidence

- Tests accept an exact source-bound archive.
- Tests reject changed, missing, and additional source payloads.
- The current sdist binds 1117 reviewed repository files.
- Wheel roundtrip and wheel source binding remain independently mandatory.
- Topology, metadata, root, resource, and reproducibility gates compose.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
