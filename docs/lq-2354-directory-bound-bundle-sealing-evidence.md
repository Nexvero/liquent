# LQ-2354 Directory-bound bundle-sealing evidence

- Focused tests retain valid sealing, private mode, and digest checks.
- Existing tests reject symbolic links, hard links, and oversized bundles.
- A source-boundary test proves directory-relative no-follow opening and excludes
  the prior full-path bundle open.
- Candidate identity and terminal inventory checks remain independently active.
- Production readiness remains false; publication and promotion remain separate.
