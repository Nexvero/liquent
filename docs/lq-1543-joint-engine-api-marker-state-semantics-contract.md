# LQ-1543 Joint engine API marker state semantics contract

- Marker state must describe one canonical owner-private file.
- File type, owner, mode, link count, and size are mandatory.
- Size must equal the canonical encoded acceptance length.
- Identity must remain the state device and inode prefix.
- Invalid semantics fail through the unavailable boundary.
- State grants no authorization or caller influence.
- Existing descriptor capture remains authoritative.
