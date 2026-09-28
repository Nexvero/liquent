# LQ-1531 Joint engine API source state semantics contract

- Source state must describe the fixed owner-private layout.
- Root state must identify an owner-private directory.
- Child state must identify owner-private regular files.
- Every child must have exactly one link.
- Child size must remain inside its fixed source limit.
- Invalid semantics fail through the unavailable boundary.
- State remains evidence and never caller authority.
