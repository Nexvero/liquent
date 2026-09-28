# LQ-2453 Terminal child-descriptor stability gate

- Each open child descriptor is measured immediately after opening.
- Type, exact 0700 mode, current owner, device, and inode must match expectations.
- After all opens, every descriptor is measured a second time while still held.
- Identity, mode, and ownership must remain unchanged through the whole set check.
- Descriptors close only after success or detail-limited rejection cleanup.
- Publication rename follows only a stable complete child-descriptor set.
