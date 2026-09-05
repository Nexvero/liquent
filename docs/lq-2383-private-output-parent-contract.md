# LQ-2383 Private output-parent contract

- Controlled preflight output may be created only below a current-user-owned
  directory with mode exactly 0700.
- The parent is opened with directory-only and no-follow semantics.
- Output target absence is measured relative to that descriptor without following
  a target symbolic link.
- Existing targets and non-private or redirected parents fail closed.
- The current local user remains the private parent trust boundary.
