# LQ-2433 Post-rename child-identity gate

- After rename, publication opens the output relative to the same parent descriptor.
- The published root must retain the original workspace device and inode.
- Every fixed child must retain its precommit device and inode at the new name.
- Verification occurs before publication returns a successful evidence path.
- Root or child identity drift after rename therefore fails closed.
- No copy, fallback rename, overwrite, deployment, or promotion path is introduced.
