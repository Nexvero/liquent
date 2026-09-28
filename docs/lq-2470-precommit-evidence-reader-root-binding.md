# LQ-2470 Precommit evidence-reader root binding

- The first readback receives identity captured at temporary workspace creation.
- It also receives evidence identity captured by the exclusive writer.
- Both parent and file identities must match before precommit inventory begins.
- The returned file identity must equal the writer result once more.
- Only this jointly bound result enters publication state.
- Missing or mismatched parent state prevents the terminal commit boundary.
