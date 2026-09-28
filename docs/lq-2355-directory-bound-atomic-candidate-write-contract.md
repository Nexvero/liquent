# LQ-2355 Directory-bound atomic candidate-write contract

- Atomic candidate-file creation is bound to one private output directory identity.
- The directory is opened without symbolic-link traversal and must retain its
  measured device and inode before publication completes.
- Target absence is checked relative to that open descriptor without following a
  target symbolic link.
- No path-based existence decision authorizes creation.
- The writer remains local and creates no publication authority.
