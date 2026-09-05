# LQ-2388 Private workspace-root entry gate

- The four expected root directories must be real current-user-owned directories
  with mode exactly 0700.
- The controlled evidence entry must be a current-user-owned mode-0600 regular file,
  singly linked, non-empty, and within its existing size ceiling.
- Entry metadata is resolved relative to the bound workspace without following links.
- The wheel installation target is created privately before `pip` writes into it.
- No permission repair occurs at the terminal gate.
