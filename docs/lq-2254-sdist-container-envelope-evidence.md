# LQ-2254 sdist container-envelope evidence

- Tests accept the normalizer's minimal record-aligned TAR output.
- A second valid gzip member is rejected.
- An additional all-zero TAR record is rejected.
- A nonzero byte in physical record padding is rejected.
- Existing tests retain bounded gzip header and trailer evidence.
- Existing manifest tests retain member and payload identity evidence.
- External signing and publication evidence remain open; production_ready=false.
