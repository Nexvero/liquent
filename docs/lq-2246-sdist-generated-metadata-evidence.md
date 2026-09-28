# LQ-2246 sdist generated-metadata evidence

- Tests accept a complete internally consistent generated metadata set.
- Tests reject PKG-INFO, entry-point, requirement, setup, and top-level drift.
- Real sdist and wheel metadata are byte-consistent at every redundant edge.
- Source, roundtrip, topology, metadata, bounds, and reproducibility compose.
- The generated metadata digest remains private preflight run state.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
