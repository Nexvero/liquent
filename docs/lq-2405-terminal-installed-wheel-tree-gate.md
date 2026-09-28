# LQ-2405 Terminal installed-wheel tree gate

- The entry-point phase retains canonical tree SHA-256, file count, and total bytes.
- The bundle phase traverses the private tree again without normalization.
- Every directory must remain 0700 and every file 0600, current-user-owned, regular,
  singly linked, bounded, and stable while read.
- Digest, file count, and total bytes must equal the retained measurements.
- Drift prevents candidate construction and terminal success.
