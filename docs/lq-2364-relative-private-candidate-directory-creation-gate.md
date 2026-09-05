# LQ-2364 Relative private candidate-directory creation gate

- The fixed `bundle` child directory is created exclusively with mode 0700 relative
  to the bound workspace descriptor.
- A pre-existing child of any type is rejected and never reused or replaced.
- The created child is independently opened without following links and measured as
  a private output-directory identity.
- Parent-directory synchronization occurs before the child is returned.
- No caller-selected child name is accepted.
