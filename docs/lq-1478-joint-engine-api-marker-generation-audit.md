# LQ-1478 Joint engine API marker generation audit

- LQ-1475 through LQ-1477 close same-content marker replacement.
- Audit evidence now binds registry root, marker generation, and value.
- Path and byte equality cannot substitute for inode continuity.
- Existing read integrity and visible-root checks remain mandatory.
- Failure remains fail-closed and detail-free.
- No new recovery, deletion, or rewrite behavior was introduced.
- Operation integration remains the final strand boundary.
