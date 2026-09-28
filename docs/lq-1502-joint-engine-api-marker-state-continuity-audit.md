# LQ-1502 Joint engine API marker state continuity audit

- LQ-1499 through LQ-1501 close same-inode marker rewrite windows.
- Accepted audit binds canonical value, identity, and descriptor state.
- Restored bytes cannot hide intervening status changes.
- Existing fail-closed and detail-free behavior is preserved.
- No new cleanup, mutation, or recovery semantics were added.
- Registry and source continuity remain independently required.
- One-shot record comparison is the remaining strand boundary.
