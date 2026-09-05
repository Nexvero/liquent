# LQ-2035 Joint engine API direct request preflight contract

- Every direct request is validated before clock or I/O.
- Root must be a Path instance.
- Root must be absolute and non-root.
- Root must contain no parent traversal component.
- Audit mode must be exact boolean.
- Invalid input fails detail-free.
- Public signatures remain unchanged.
