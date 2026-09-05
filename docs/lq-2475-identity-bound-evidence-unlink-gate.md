# LQ-2475 Identity-bound evidence-unlink gate

- Cleanup inspects the fixed evidence entry relative to the held workspace descriptor.
- It does not follow symbolic links and accepts only a regular matching device/inode.
- Only that matching entry may be unlinked.
- The workspace directory is synchronized after successful unlink.
- Missing, replaced, redirected, or special entries cause a non-destructive return.
- Cleanup errors never trigger recursive deletion or an alternate path fallback.
