# LQ-2193 sdist late reverification gate

- The sdist gate requires path, manifest, root, and epoch together.
- It reruns normalized header, metadata, topology, and manifest checks.
- Structural package checks execute only after continuity succeeds.
- The reported hash therefore covers the same verified artifact.
- Missing context and changed bytes use detail-limited rejection.
- No trust is inferred from an artifact basename alone.
- Later bundle behavior remains unchanged.
