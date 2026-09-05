# LQ-2468 Pre-read workspace-identity gate

- The reader opens the workspace itself without following symbolic links.
- Its descriptor must identify the controller-retained device and inode.
- Exact mode 0700 and current-user ownership remain independently mandatory.
- Evidence opening cannot begin beneath a replacement directory object.
- Path equality and a matching child inode are insufficient.
- Identity mismatch remains one detail-limited controlled-preflight rejection.
