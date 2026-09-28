# LQ-2425 Terminal roundtrip-directory identity gate

- The sdist phase retains the private roundtrip parent device and inode.
- The bundle phase requires that retained identity before inventory starts.
- Terminal one-file inventory verifies the same directory identity explicitly.
- A byte-identical wheel in a newly created same-named directory is rejected.
- Existing exact name, mode, ownership, link, size, and digest checks remain active.
- Candidate construction follows both parent continuity and content verification.
