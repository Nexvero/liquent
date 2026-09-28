# LQ-2456 Retained controlled-evidence identity gate

- The no-follow evidence verifier returns device and inode from its stable open file.
- The controller retains that identity only after exact payload verification succeeds.
- Terminal precommit inventory compares the evidence entry to the retained identity.
- Missing identity, replacement, hard-link drift, or metadata drift fails closed.
- The identity travels separately from the canonical evidence payload.
- No caller-provided identity or success claim enters this state.
