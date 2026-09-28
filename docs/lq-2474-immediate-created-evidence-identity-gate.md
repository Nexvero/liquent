# LQ-2474 Immediate created-evidence identity gate

- The writer measures its descriptor immediately after exclusive creation and chmod.
- The new object must be regular, private, current-user-owned, singly linked, and empty.
- Device and inode are retained before the first payload write can fail.
- Later successful metadata checks still independently validate final size and mode.
- An invalid initial object fails closed before accepting any written evidence bytes.
- No path lookup establishes this initial cleanup identity.
