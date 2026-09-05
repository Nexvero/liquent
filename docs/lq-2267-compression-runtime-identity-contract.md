# LQ-2267 compression-runtime identity contract

- Canonical release bytes depend on an explicitly measured runtime identity.
- Python is bound at major, minor, and patch level.
- zlib build and loaded runtime versions are separate required facts.
- Build-time and runtime zlib identities must both match reviewed values.
- A compatible-looking but different version is not accepted implicitly.
- Runtime facts grant no authority to build, sign, or publish artifacts.
- Version changes require a separate reviewed contract update.
