# LQ-2278 distribution-pair identity evidence

- Tests accept a matching named and versioned artifact pair.
- A wheel/sdist version mismatch is rejected.
- A non-Liquent wheel filename is independently rejected.
- Existing tests reject replacement of either captured byte stream.
- Distribution-phase facts expose version and canonical pair SHA-256.
- Real wheel and sdist identities remain unchanged.
- External signing and publication evidence remain open; production_ready=false.
