# LQ-1340 Descriptor-relative joint engine API operation root

- Root acquisition walks from the filesystem root one component at a time.
- Every component opens as a directory with no-follow and close-on-exec.
- Prior traversal descriptors close immediately after successful descent.
- Final validation repeats the complete no-follow component walk.
- Initial, held-final, and visible-final root metadata must agree.
- Exact inventories are checked through both final root descriptors.
- The public operation-root API remains unchanged.
