# LQ-1977 Joint engine API accept UTC reader

- Accept reader delegates to one-shot UTC source.
- Returned value crosses shared UTC validator.
- Initial decision time uses validated reader.
- Verification and final times use same reader.
- Inner verifier clock behavior remains independent.
- No malformed outer value reaches comparison.
- Existing freshness semantics remain unchanged.
