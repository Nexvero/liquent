# LQ-1438 Joint engine API expected source identity audit

- LQ-1435 through LQ-1437 close source-loader identity comparison.
- The comparison is against the directory descriptor actually used.
- Path continuity or equal bytes cannot replace identity continuity.
- All pre-existing source integrity checks remain mandatory.
- Optional binding preserves the standalone verification boundary.
- No new exception, persistence, or deployment choice was added.
- Outer-to-inner propagation remains the next required boundary.
