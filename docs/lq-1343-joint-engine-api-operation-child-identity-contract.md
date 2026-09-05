# LQ-1343 Joint engine API operation child identity contract

- `source-set` and `accepted-runs` are fixed operation-root children.
- Each child must be an owner-private real directory.
- Device and inode identity are captured through descriptor-relative opens.
- Final visible child identities must equal their initial identities.
- Identical copied content cannot transfer a child's identity.
- Child replacement invalidates the whole operation-root binding.
- No caller-supplied child path or identity is accepted.
