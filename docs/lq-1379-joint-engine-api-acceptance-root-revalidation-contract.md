# LQ-1379 Joint engine API acceptance root revalidation contract

- The visible acceptance root is re-opened after each registry operation.
- Final traversal repeats complete no-follow component enforcement.
- Held and visible device, inode, mode, owner, group, and link facts agree.
- A missing, replaced, or symlink-rebound visible path fails closed.
- Final validation never supplies a descriptor for marker access.
- The working descriptor remains the sole read or write authority.
- Revalidation runs before successful operation return.
