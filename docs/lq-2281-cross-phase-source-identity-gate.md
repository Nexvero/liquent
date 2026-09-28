# LQ-2281 cross-phase source-identity gate

- The common phase executor captures or rechecks the source commit first.
- Commit mismatch rejects before phase-specific measurement begins.
- Once established, the source epoch is also checked before measurement.
- Missing or changed epoch text rejects fail closed.
- These checks cover tests, distributions, artifacts, and bundle phases.
- Phase facts continue to carry the same source commit independently.
- Rejection is detail-limited and causes no repository mutation.
