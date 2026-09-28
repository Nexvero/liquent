# LQ-2498 Prephase exact workspace-entry gate

- Before each gate, root entries must equal the current captured-directory names.
- The workspace descriptor must retain bound identity, mode 0700, and current owner.
- Every listed child is inspected without following symbolic links.
- Each must be a real directory with exact mode 0700 and current owner.
- Entry names are measured again before the descriptor closes.
- Prephase mismatch prevents the next trusted gate from executing.
