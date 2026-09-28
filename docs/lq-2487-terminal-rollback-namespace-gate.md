# LQ-2487 Terminal rollback-namespace gate

- Safe rollback requires the private workspace name to be absent before rename.
- The output must be the exact retained workspace directory object.
- After relative rename and parent sync, the private name is measured again.
- Its device and inode must equal the retained workspace identity.
- The public output name must then be absent and parent identity unchanged.
- Any ambiguity yields a false result without destructive correction.
