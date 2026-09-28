# LQ-2287 build-runtime digest contract

- Build provenance includes one canonical runtime-environment digest.
- Facts include exact Python, zlib build, zlib runtime, and tool versions.
- The existing canonical serializer orders the nested tool mapping.
- SHA-256 of those facts is the build-runtime identity.
- Raw host paths, environment variables, and machine names are excluded.
- The digest is evidence and grants no build or publication authority.
- Any reviewed runtime update necessarily creates a new identity.
