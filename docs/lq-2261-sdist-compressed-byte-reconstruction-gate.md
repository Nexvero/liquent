# LQ-2261 sdist compressed-byte reconstruction gate

- The verifier first obtains the bounded canonical TAR byte stream.
- It recompresses those bytes with the shared canonical renderer.
- Acceptance requires equality with every candidate gzip byte.
- Valid alternate Deflate encodings therefore fail closed.
- Header, member-count, trailer, TAR, and manifest gates remain independent.
- A mismatch exposes no artifact detail beyond ordinary gate rejection.
- Verification never replaces or rewrites the supplied candidate.
