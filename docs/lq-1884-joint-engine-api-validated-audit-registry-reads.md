# LQ-1884 Joint engine API validated audit registry reads

- Registry audit uses the shared reader three times.
- Accepted-source audit uses the shared reader three times.
- Initial result capture is validated immediately.
- Success and terminal context rereads are validated immediately.
- Equality checks consume canonical evidence only.
- Both audit modes remain read-only.
- Existing timing budgets remain unchanged.
