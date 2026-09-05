# LQ-2288 runtime-phase digest capture gate

- Runtime facts are validated before their digest is captured.
- All four locked package tool versions participate in the digest.
- Python and both zlib identities participate independently.
- The digest is stored only in private preflight run state.
- Runtime-phase facts expose the resulting digest for evidence hashing.
- Missing package or version drift prevents digest establishment.
- No caller-supplied runtime digest is accepted.
