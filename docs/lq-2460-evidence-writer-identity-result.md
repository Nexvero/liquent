# LQ-2460 Evidence-writer identity result

- The existing path-only writer remains a compatibility wrapper for focused helpers.
- Controlled execution uses the identity-returning exclusive writer directly.
- Its result contains the fixed evidence path and descriptor-derived device/inode pair.
- No caller-selected filename, identity, mode, or replacement behavior is introduced.
- Failed writes still remove only the newly created relative entry.
- Successful return follows file and directory synchronization.
