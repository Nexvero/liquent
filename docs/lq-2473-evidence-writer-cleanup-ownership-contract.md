# LQ-2473 Evidence-writer cleanup ownership contract

- Failed evidence creation may remove only the file object created by that writer.
- A fixed name or successful exclusive open alone cannot authorize later unlink.
- Device and inode are captured immediately from the new write descriptor.
- Cleanup compares the current relative entry to that captured identity.
- Replacement, disappearance, or type drift prevents unlink and preserves current data.
- This narrow cleanup authority grants no broader deletion or publication capability.
