# LQ-2330 Descriptor-bound inventory evidence

- Focused tests preserve deterministic identity for the valid three-file output.
- They prove rejection of candidate-file mode drift and external hard links.
- A source-boundary test proves directory-relative, no-follow file opening and
  excludes path-based candidate reads from the inventory implementation.
- Existing tests continue to reject extra, missing, and symbolic-link entries.
- Production readiness remains false; promotion and publication remain separate.
