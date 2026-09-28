# LQ-2272 distribution-pair capture gate

- Digests are captured only after one wheel and one sdist are present.
- The sdist is normalized before its final digest is captured.
- Source and generated-metadata parity pass before pair completion.
- Both paths and both digests stay private to the preflight context.
- An incomplete pair is indistinguishable from an unusable pair downstream.
- Caller-supplied digests are not accepted by the gate.
- Existing distribution-phase facts expose both resulting digests.
