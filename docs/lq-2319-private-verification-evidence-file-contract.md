# LQ-2319 private verification-evidence file contract

- `verification.json` resides in the private candidate output directory.
- It is one regular owner-controlled file with exact mode `0600`.
- Exactly one directory entry may link to its inode.
- Canonical payload size is positive and at most 16 KiB.
- Complete bytes remain bound by the captured verification SHA-256.
- The report contains evidence and grants no release authority.
- External evidence persistence remains a separate boundary.
