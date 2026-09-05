# LQ-2480 Pre-unlink workspace-metadata gate

- Cleanup first measures the still-open workspace directory descriptor.
- Device and inode must match the writer's initial parent measurement.
- Mode must remain exactly 0700 and owner must remain the current user.
- These checks precede inspection of the fixed evidence entry.
- Failure returns non-destructively without unlink or alternate path lookup.
- The original controlled rejection remains the only caller-visible result.
