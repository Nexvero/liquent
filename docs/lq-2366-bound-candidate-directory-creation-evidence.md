# LQ-2366 Bound candidate-directory creation evidence

- Focused tests prove a private relative child and its measured identity.
- They prove fail-closed rejection of an existing child and symbolic-link workspace.
- A source-boundary test proves descriptor-relative creation and rollback while
  excluding the previous path-based child creation.
- All downstream private-directory and candidate-file checks remain active.
- Production readiness remains false; publication and promotion remain separate.
