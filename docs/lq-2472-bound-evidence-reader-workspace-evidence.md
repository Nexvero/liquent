# LQ-2472 Bound evidence-reader workspace evidence

- Focused tests move the original evidence inode into a replacement workspace.
- File bytes and identity still match, but parent identity causes rejection.
- Source checks retain parent identity checks before and after every read.
- Controlled precommit and published readback both pass the bound workspace identity.
- Existing writer, inventory, metadata, synchronization, and rollback checks remain active.
- Production readiness remains false; deployment and external publication remain forbidden.
