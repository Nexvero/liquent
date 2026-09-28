# LQ-2271 distribution artifact-pair identity contract

- One build phase establishes exactly one wheel and one sdist identity.
- Each identity is the SHA-256 digest of the complete canonical artifact.
- The two identities form one inseparable in-memory distribution pair.
- A later path match does not substitute for byte identity.
- Replacing either artifact invalidates the pair fail closed.
- Pair identity is evidence and grants no signing or publication authority.
- Cross-run persistence and release registration remain separate concerns.
