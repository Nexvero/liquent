# LQ-2507 Same-name intermediate replacement rejection

- Removing a captured output directory does not release its trusted identity.
- Recreating its name with mode 0700 and the current owner is insufficient.
- Device and inode mismatch causes detail-limited fail-closed rejection.
- The replacement cannot be adopted by a later phase or receipt.
- Existing phase order and single mapped capture remain unchanged.
- Temporary-workspace cleanup handles rejected local state normally.
