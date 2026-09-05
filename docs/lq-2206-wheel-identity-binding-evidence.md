# LQ-2206 Wheel identity binding evidence

- Tests reject foreign project names and incompatible wheel tags.
- Tests reject filename, dist-info, Name, and Version disagreement.
- A canonical minimal Liquent wheel remains accepted.
- Real direct and sdist-roundtrip wheels satisfy the identity chain.
- Existing integrity, topology, size, and content gates remain composed.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
