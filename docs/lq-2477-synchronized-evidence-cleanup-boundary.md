# LQ-2477 Synchronized evidence-cleanup boundary

- Successful identity-bound unlink is followed by workspace-directory synchronization.
- Cleanup uses the same directory descriptor that performed exclusive creation.
- File disappearance becomes durable before rejection escapes when synchronization works.
- Synchronization failure does not authorize a second path or destructive retry.
- The surrounding temporary workspace remains responsible for later normal cleanup.
- Successful evidence creation never enters this failure-only boundary.
