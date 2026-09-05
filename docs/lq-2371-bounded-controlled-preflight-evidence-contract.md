# LQ-2371 Bounded controlled-preflight evidence contract

- Canonical controlled-preflight evidence must be non-empty and no larger than
  64 KiB.
- The same bound applies during exclusive creation and terminal verification.
- Oversized evidence is rejected before a file is created or trusted.
- The bound covers local orchestration evidence only and changes no gate receipts.
- Evidence continues to forbid publishing and deployment authority.
