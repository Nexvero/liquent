# LQ-1505 Joint engine API recorded marker state evidence

- Tests rewrite and restore the marker after durable record returns.
- Marker inode and canonical final bytes remain the same.
- Recorded and final descriptor states differ, causing rejection.
- Stable marker state allows one-shot acceptance and later audit.
- Prior generation and root replacement tests remain green.
- Focused verification passes 52 tests under strict warnings.
- External image and staging evidence remains absent.
