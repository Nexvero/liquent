# LQ-2530 Capture parent-continuity gate

- Workspace metadata is measured before and after child capture operations.
- Both parent observations must retain the bound device and inode identity.
- Exact mode 0700 and current local ownership are required in both observations.
- Parent drift invalidates capture even when child identity appears unchanged.
- The same open workspace descriptor anchors both parent measurements.
- No later intermediate verification repairs a failed capture.
