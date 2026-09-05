# LQ-2343 Directory-bound verification-evidence contract

- Verification-evidence validation uses the previously bound private output
  directory identity.
- The parent is opened as a directory without following symbolic links.
- Its open device and inode must equal the identity established by the bundle gate.
- `verification.json` is resolved only relative to that descriptor.
- The contract introduces no new evidence source or publication authority.
