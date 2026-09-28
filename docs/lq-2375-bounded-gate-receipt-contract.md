# LQ-2375 Bounded gate-receipt contract

- Every controlled preflight gate returns one non-empty bytes receipt no larger
  than 1024 bytes.
- The bound applies before decoding or structural interpretation.
- Empty, oversized, or non-bytes values fail closed without receipt acceptance.
- The resource ceiling is local orchestration policy and grants no authority.
- Gate facts remain represented only by their existing SHA-256 digest.
