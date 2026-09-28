# LQ-2363 Private preflight-workspace contract

- Candidate-output creation begins only within the orchestrator-provided workspace.
- The workspace must be a current-user-owned directory with mode exactly 0700.
- It is opened with directory-only and no-follow semantics before child creation.
- Its device and inode become the bound parent identity for this operation.
- A missing, redirected, or non-private workspace fails closed.
