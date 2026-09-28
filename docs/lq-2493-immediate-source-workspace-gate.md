# LQ-2493 Immediate source-workspace gate

- The source relative name is measured again immediately before rename.
- It must remain a real directory with mode 0700 and current-user ownership.
- Device and inode must equal the workspace identity retained at creation.
- A replacement source cannot pass through an unchanged path string.
- This check follows descriptor-bound child verification and precedes target absence.
- Failure leaves both private source and any existing target untouched.
