# LQ-2302 release-candidate identity evidence

- Tests establish one candidate from pair, report, bundle, source, and version.
- Replacing report bytes without its captured digest is rejected.
- Changing valid bundle bytes changes candidate identity.
- Changing valid pair identity independently changes candidate identity.
- Changing valid report identity independently changes candidate identity.
- Existing bundle integrity still reports `promotable=false`.
- External signing and publication evidence remain open; production_ready=false.
