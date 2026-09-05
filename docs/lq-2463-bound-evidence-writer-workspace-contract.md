# LQ-2463 Bound evidence-writer workspace contract

- Evidence creation occurs only in the controller-bound workspace directory object.
- A private mode, current owner, or matching path cannot substitute for root identity.
- The writer accepts expected workspace device and inode as internal trusted state.
- It checks that identity before exclusive file creation and after synchronization.
- Replacement, deletion and recreation, or redirection fails closed without evidence.
- This local writer binding grants no deployment or external publication authority.
