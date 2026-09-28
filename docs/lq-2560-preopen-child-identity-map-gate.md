# LQ-2560 Preopen child-identity map gate

- Every value in the snapshotted expected mapping is validated together.
- One invalid child identity rejects the complete verifier invocation.
- Validation precedes workspace opening and all child-name resolution.
- Fixed valid names do not make malformed identity values acceptable.
- No partially valid subset proceeds to filesystem inspection.
- The source mapping remains externally owned and unmodified.
