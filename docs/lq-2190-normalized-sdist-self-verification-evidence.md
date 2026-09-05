# LQ-2190 Normalized sdist self-verification evidence

- Tests accept a fully matching normalized output manifest.
- Tests reject payload-manifest and fixed-epoch mismatches.
- Out-of-range Gzip epochs fail before archive reading or writing.
- Existing topology, metadata, root, and resource gates are reused.
- The real repository build passes normalization and self-verification.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
