# LQ-2436 Identity-bound publication rollback gate

- Rollback starts only after the forward relative rename completed.
- The temporary workspace name must still be absent.
- The output must be a real directory with the retained workspace device and inode.
- Only then is output renamed back to the original private temporary name.
- The common parent directory is synchronized after successful rollback.
- Identity mismatch, ambiguity, or filesystem failure causes no destructive fallback.
