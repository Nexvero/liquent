# LQ-2282 source-run binding evidence

- Tests establish one clean source commit for a probe phase.
- A subsequent different clean commit is rejected.
- Tests independently mutate the bound SOURCE_DATE_EPOCH value.
- Epoch mutation is rejected before probe measurement.
- Existing phase tests retain clean-tree and canonical fact evidence.
- Artifact digests and pair identity remain unchanged by this binding.
- External signing and publication evidence remain open; production_ready=false.
