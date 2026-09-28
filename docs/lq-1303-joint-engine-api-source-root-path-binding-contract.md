# LQ-1303 Joint engine API source root path binding contract

- A source snapshot is bound to both its opened root and visible root path.
- The visible path must still identify the opened directory after capture.
- Device and inode identity are internal facts, never caller assertions.
- A missing, replaced, or symlink-rebound path fails closed.
- Stable descriptor contents alone are insufficient after path rebinding.
- Rejection exposes no partial snapshot or filesystem detail.
- Existing ownership, privacy, inventory, and budget rules remain additive.
