# LQ-2356 Private relative temporary-file gate

- A cryptographically random temporary name is created exclusively relative to the
  bound directory descriptor.
- The temporary file is opened without symbolic-link traversal and forced to mode
  0600 before payload writing.
- Type, owner, mode, single-link state, and exact size are checked after file sync.
- Short or failed writes are rejected without publishing a target.
- Temporary residue is removed through the same directory descriptor.
