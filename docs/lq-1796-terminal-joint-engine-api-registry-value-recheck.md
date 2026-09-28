# LQ-1796 Terminal joint engine API registry value recheck

- Terminal inspection reloads canonical acceptance values.
- It uses the fixed resolved acceptance root.
- The original root identity remains mandatory.
- Returned values must equal the result projection.
- Addition, removal, replacement, or reordering is rejected.
- No caller-provided inventory participates.
- Existing inspection semantics remain unchanged.
