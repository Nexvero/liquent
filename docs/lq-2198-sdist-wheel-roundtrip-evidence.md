# LQ-2198 sdist wheel roundtrip evidence

- Tests require the late gate to execute the private wheel rebuild.
- Tests bind its output to the direct distribution wheel bytes.
- A changed canonical sdist still fails before rebuilding.
- The real repository sdist rebuilds a byte-identical wheel.
- Both direct and rebuilt wheels pass the existing verifier.
- No signing, upload, container, or deployment operation is added.
- Production readiness still requires external release evidence.
