# LQ-2218 Wheel source epoch binding evidence

- Tests cover UTC conversion and exact ZIP-resolution rounding.
- Tests reject pre-1980, negative, boolean, and oversized epochs.
- Tests reject a canonical wheel carrying the wrong uniform timestamp.
- Real direct and roundtrip wheels match the reviewed source epoch.
- ZIP metadata, RECORD, identity, topology, and bounds remain composed.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
