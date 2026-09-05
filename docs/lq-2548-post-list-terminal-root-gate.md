# LQ-2548 Post-list terminal root gate

- Final workspace metadata is measured only after the third listing succeeds.
- Device and inode must retain the controller-bound workspace identity.
- Exact mode 0700 and current local ownership remain mandatory.
- Root drift caused during final listing is therefore measured afterward.
- The same held descriptor anchors listing and terminal metadata.
- Descriptor cleanup follows every root-gate outcome.
