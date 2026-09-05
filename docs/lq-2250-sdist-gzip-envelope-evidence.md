# LQ-2250 sdist gzip envelope evidence

- Tests pin all ten canonical header bytes for the normalized sdist.
- Mutated XFL and OS bytes are independently rejected.
- A mutated trailer checksum is rejected before manifest acceptance.
- A lowered expansion ceiling proves fail-closed uncompressed-size handling.
- Existing normalization tests retain byte-identical double-build evidence.
- Existing manifest checks still bind TAR names, metadata, and payload bytes.
- External signing and publication evidence remain open; production_ready=false.
