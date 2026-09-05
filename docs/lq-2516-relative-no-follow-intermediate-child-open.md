# LQ-2516 Relative no-follow intermediate child open

- Child names are resolved only relative to the held workspace descriptor.
- Opens require read-only directory semantics and no symbolic-link following.
- Missing, linked, non-directory, or inaccessible children fail closed.
- Expected names remain restricted to fixed controller-owned phase outputs.
- No absolute reconstructed child path establishes trusted identity.
- Operating-system failures retain the existing detail-limited rejection boundary.
