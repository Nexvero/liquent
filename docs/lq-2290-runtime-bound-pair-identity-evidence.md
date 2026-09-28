# LQ-2290 runtime-bound pair-identity evidence

- Tests capture one 64-character runtime digest from reviewed facts.
- Tests hold source and artifacts fixed while changing runtime identity.
- The changed runtime identity produces a different pair SHA-256.
- Existing tests retain source, name, version, and byte replacement checks.
- Runtime drift remains rejected before artifact construction.
- Real artifact byte digests remain unchanged by provenance extension.
- External signing and publication evidence remain open; production_ready=false.
