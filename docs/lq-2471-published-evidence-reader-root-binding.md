# LQ-2471 Published evidence-reader root binding

- Final-path readback receives the original temporary workspace identity.
- Relative rename must preserve that directory object beneath the output name.
- The reader requires both published-root identity and retained evidence identity.
- A moved evidence inode inside a foreign replacement output still fails closed.
- Failure remains inside the identity-bound publication rollback boundary.
- Successful return follows parent, file, payload, and inventory agreement.
