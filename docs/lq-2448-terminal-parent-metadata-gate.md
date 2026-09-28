# LQ-2448 Terminal parent-metadata gate

- After readback and inventory, the open parent descriptor is measured again.
- Its device and inode must equal the identity bound before workspace creation.
- Its mode must still be exactly 0700 and owner must be the current user.
- A late permission or ownership change prevents publication success.
- Failure enters identity-bound rollback without selecting another parent.
- Existing parent synchronization and relative-name checks remain active.
