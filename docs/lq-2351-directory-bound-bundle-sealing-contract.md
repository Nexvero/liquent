# LQ-2351 Directory-bound bundle-sealing contract

- Bundle sealing is bound to the private output directory identity measured before
  the bundle was created.
- The parent is opened as a directory without symbolic-link traversal.
- Its open device and inode must match the established identity.
- The bundle is resolved only relative to that directory descriptor.
- Sealing remains local and grants no promotion or publication authority.
