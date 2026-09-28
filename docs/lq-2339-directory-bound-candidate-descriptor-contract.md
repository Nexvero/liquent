# LQ-2339 Directory-bound candidate-descriptor contract

- Descriptor verification binds the previously measured private parent directory.
- The parent is opened as a directory without symbolic-link traversal.
- Its open descriptor must retain the expected device and inode identity.
- Candidate resolution occurs relative to that descriptor, not through a renewed
  absolute or caller-influenced path traversal.
- This binding grants no publication or promotion authority.
