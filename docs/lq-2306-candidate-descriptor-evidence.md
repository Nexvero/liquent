# LQ-2306 candidate-descriptor evidence

- Tests atomically create one canonical candidate descriptor.
- Its complete-file SHA-256 equals the candidate identity.
- Independent descriptor verification accepts the exact bytes.
- A second write to the same path is rejected without overwrite.
- Existing tests retain bundle, pair, report, source, and version binding.
- No signing material or promotion decision enters the descriptor.
- External signing and publication evidence remain open; production_ready=false.
