# LQ-2464 Prewrite workspace-identity gate

- The writer opens the workspace without following links before creating evidence.
- Its open descriptor must match the controller-retained device and inode.
- Exact 0700 mode and current-user ownership remain independently mandatory.
- Identity mismatch is rejected before the fixed evidence name is opened.
- The compatibility path-only writer supplies no synthetic expected identity.
- Controlled execution always supplies its previously retained workspace identity.
