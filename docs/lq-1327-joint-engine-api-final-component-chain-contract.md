# LQ-1327 Joint engine API final component chain contract

- The complete source-root component chain is re-opened after capture.
- Final traversal uses the same descriptor-relative no-follow policy.
- The final leaf must retain the initially opened device and inode.
- Parent disappearance, replacement, or symlink rebinding fails closed.
- A stable original descriptor alone cannot complete the operation.
- Final path trust is derived from filesystem facts, not caller input.
- No partial source snapshot becomes observable after rejection.
