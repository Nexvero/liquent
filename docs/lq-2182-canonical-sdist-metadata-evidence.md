# LQ-2182 Canonical sdist metadata evidence

- Tests reject Unicode normalization and control aliases.
- Tests reject noncanonical and privileged file or directory modes.
- Tests accept exact long paths and bounded finite source mtime only.
- Unknown and mismatched extended metadata fails closed.
- The real repository sdist satisfies the complete metadata gate.
- Reproducibility, topology, and resource bounds remain composed.
- Production readiness still requires external release evidence.
