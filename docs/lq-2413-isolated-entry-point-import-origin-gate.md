# LQ-2413 Isolated entry-point import-origin gate

- The loader interpreter uses isolated mode and ignores `PYTHONPATH` injection.
- It explicitly places the bound private installation root first on its import path.
- Every exact expected entry point must load to a callable object.
- Every callable module file must resolve strictly beneath that installation root.
- Source-checkout, user-site, missing, and non-file-backed origins fail closed.
- Loading still executes no command and grants no operator or publication authority.
