# LQ-2173 Atomic sdist normalization failure

- The original sdist remains authoritative until replacement succeeds.
- Rejected input never overwrites the original archive.
- A private sibling temporary file receives normalized bytes.
- Replacement is atomic within the private artifact directory.
- Failed writes and validation remove temporary residue.
- No source-tree path is created, changed, or removed.
- Technical failure remains the existing detail-limited rejection.
