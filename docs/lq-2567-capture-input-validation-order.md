# LQ-2567 Capture input-validation order

- Workspace identity validity is evaluated before fixed-name acceptance.
- Exact string type is established before set membership is attempted.
- Only fully valid inputs may proceed to the workspace descriptor open.
- Filesystem state never participates in deciding malformed input validity.
- Descriptor-based continuity checks remain unchanged after the preopen gate.
- Returned identity still requires the complete successful capture lifecycle.
