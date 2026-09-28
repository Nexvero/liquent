# LQ-2509 Intermediate child-stability contract

- One successful metadata pass is insufficient for intermediate continuity.
- A stable name set must be followed by a second complete child inspection.
- Both passes bind every fixed name to the same captured device and inode.
- Type, exact private mode, and current owner remain mandatory in both passes.
- Workspace metadata is measured again after the second child pass.
- This local stability evidence grants no release or deployment authority.
