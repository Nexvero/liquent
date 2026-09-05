# LQ-2294 quality-bound pair-identity evidence

- Tests pin both test commands, counts, warnings, and PostgreSQL version.
- Tests hold artifacts, source, and runtime fixed across comparison.
- Changing only quality identity changes the pair SHA-256.
- Existing checks retain commit, epoch, runtime, name, and byte binding.
- Quality capture cannot occur from incomplete test state.
- Real artifact byte digests remain unchanged by provenance extension.
- External signing and publication evidence remain open; production_ready=false.
