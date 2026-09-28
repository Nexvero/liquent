# LQ-1501 Joint engine API marker state continuity evidence

- Tests rewrite the existing marker without replacing its inode.
- They restore exact canonical bytes and owner-private mode afterward.
- Final state differs and the accepted-source audit rejects it.
- Stable state continues allowing the complete audit lifecycle.
- Same-content replacement coverage remains independently green.
- Existing root and source revalidation tests remain.
- Strict warning treatment guards compatibility regressions.
