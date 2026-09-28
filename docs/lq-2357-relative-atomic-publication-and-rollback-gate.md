# LQ-2357 Relative atomic publication and rollback gate

- The synchronized temporary file is hard-linked exclusively to the final name with
  both source and destination relative to the bound directory descriptor.
- The temporary name is removed before the directory is synchronized.
- A failed link, directory sync, or final directory-identity check fails closed.
- If publication occurred before failure, rollback removes the final name relative
  to the same descriptor.
- Existing files are never replaced.
