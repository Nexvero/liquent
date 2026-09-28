# LQ-2327 Directory-bound candidate inventory contract

- Candidate inventory resolution is bound to one opened private output directory.
- The directory is opened without symbolic-link traversal and must retain its
  previously measured device and inode identity.
- Enumeration and child-file resolution use that same directory descriptor.
- Path-based child reads cannot silently redirect inventory authority elsewhere.
- This contract remains local and grants no publication or promotion authority.
