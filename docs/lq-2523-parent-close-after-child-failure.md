# LQ-2523 Parent close after child failure

- The workspace descriptor receives a close attempt after all retained children.
- A prior child-close failure cannot suppress that parent-close attempt.
- Parent close is also attempted when verification itself already rejected.
- Every close outcome contributes only to one local failure decision.
- Descriptor numbers and operating-system errors remain private implementation facts.
- No automatic retry or alternate cleanup authority is introduced.
