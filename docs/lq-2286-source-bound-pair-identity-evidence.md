# LQ-2286 source-bound pair-identity evidence

- Tests hold artifact bytes and filenames constant across comparisons.
- Changing only the source commit changes the pair SHA-256.
- Changing only SOURCE_DATE_EPOCH independently changes the pair SHA-256.
- Existing tests retain name, version, and artifact-replacement rejection.
- Real artifact digests remain unchanged under the extended identity.
- The new pair digest represents provenance plus canonical artifacts.
- External signing and publication evidence remain open; production_ready=false.
