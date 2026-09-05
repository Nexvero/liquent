# LQ-2329 Cross-read candidate stability gate

- File device, inode, size, and modification time are measured before reading and
  compared with the same descriptor after hashing.
- The observed byte count must equal the bound file size and the resulting digest
  must equal the expected candidate digest.
- The exact directory entry set is checked both before and after all file reads.
- Directory identity drift, replacement, truncation, or content drift is rejected.
- No retry turns a changing candidate into an accepted candidate.
