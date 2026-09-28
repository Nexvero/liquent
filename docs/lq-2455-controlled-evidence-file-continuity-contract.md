# LQ-2455 Controlled evidence-file continuity contract

- Controlled evidence is one concrete file object from creation through publication.
- Exact bytes, mode, owner, size, and link count cannot substitute for file identity.
- Device and inode are retained after the first stable descriptor-bound readback.
- Precommit inventory and final-path readback require that same identity.
- Byte-identical deletion and recreation therefore fail closed.
- This local evidence identity grants no deployment or external publication authority.
