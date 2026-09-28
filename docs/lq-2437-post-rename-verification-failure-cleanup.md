# LQ-2437 Post-rename verification-failure cleanup

- Child or root verification failures after rename enter the rollback boundary.
- Operating-system failures in the same post-rename region use that boundary too.
- A restored workspace remains owned by the surrounding temporary-directory cleanup.
- The public output name is absent again before the rejection escapes.
- No recursive deletion, overwrite, path-based replacement, or alternate target is used.
- Successful publication remains unchanged and returns only after post-checks pass.
