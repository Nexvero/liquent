# LQ-2258 sdist TAR byte-identity evidence

- Tests prove canonical reconstruction equals normalized TAR bytes.
- An alternate valid TAR checksum spelling remains reader-compatible.
- The byte-reconstruction gate rejects that alternate spelling.
- Existing tests retain member, payload, envelope, and resource evidence.
- The real project sdist is verified after canonical reconstruction.
- No new artifact, transport, or publication side effect is introduced.
- External signing and publication evidence remain open; production_ready=false.
