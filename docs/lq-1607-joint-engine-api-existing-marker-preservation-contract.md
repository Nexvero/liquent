# LQ-1607 Joint engine API existing marker preservation contract

- Every initial marker observation must remain in final inventory.
- Value, identity, and complete state must all remain equal.
- Same-content replacement is not preservation.
- Same-inode rewrite with restored bytes is not preservation.
- Existing canonical facts cannot be removed.
- One new expected marker remains separately permitted.
- Mismatch fails detail-free.
