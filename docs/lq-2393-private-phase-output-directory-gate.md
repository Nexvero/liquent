# LQ-2393 Private phase-output directory gate

- Distribution build, wheel installation, sdist roundtrip, and bundle phases receive
  directories created through the shared private boundary.
- Build and installation tools no longer create their top-level targets implicitly.
- Creation failure or post-create identity drift triggers descriptor-relative rollback.
- Workspace and child identities are rechecked before a path is returned.
- No phase repairs an unsafe directory.
