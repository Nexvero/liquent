# LQ-2289 runtime-bound distribution-pair gate

- Pair capture requires the established build-runtime digest.
- Canonical pair facts include that digest beside source provenance.
- Every later pair check reuses the immutable captured runtime identity.
- Missing or malformed runtime identity rejects fail closed.
- Equal artifacts from a different measured runtime form another pair.
- Artifact, source, and runtime facts remain separately inspectable.
- The binding causes no artifact mutation or external registration.
