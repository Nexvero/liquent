# LQ-1513 Joint engine API one-shot source state evidence

- Tests rewrite an existing source child after marker record.
- They restore exact bytes, inode, and owner-private mode.
- Changed descriptor state causes observation inequality.
- One-shot acceptance rejects the otherwise identical snapshot.
- Stable source state continues allowing acceptance.
- Prior source-root identity tests remain green.
- Strict warning treatment guards regressions.
