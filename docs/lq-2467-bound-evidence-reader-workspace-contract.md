# LQ-2467 Bound evidence-reader workspace contract

- Evidence readback is valid only beneath the controller-bound workspace object.
- Matching evidence bytes and file identity cannot substitute for parent identity.
- The reader accepts expected workspace device and inode as trusted internal state.
- It checks that state before opening evidence and after the complete stable read.
- Moving the same file into a replacement same-named workspace fails closed.
- This local reader binding grants no deployment or external publication authority.
