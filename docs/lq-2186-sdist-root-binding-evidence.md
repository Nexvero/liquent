# LQ-2186 sdist root binding evidence

- Tests cover invalid project names and empty or unsafe versions.
- Tests derive one exact root from a valid distribution basename.
- Missing and mismatched archive root directories fail closed.
- A correctly bound root and child payload remain accepted.
- The real repository sdist satisfies the composed root gate.
- No signing, upload, container, or deployment authority is added.
- Production readiness still requires external release evidence.
