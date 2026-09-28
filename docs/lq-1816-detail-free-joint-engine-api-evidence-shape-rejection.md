# LQ-1816 Detail-free joint engine API evidence shape rejection

- Explicit validation avoids incidental unpacking errors.
- TypeError and ValueError do not escape the boundary.
- Null evidence receives no special successful meaning.
- Rejection is deterministic across malformed shapes.
- Existing unavailable semantics remain authoritative.
- No evidence values enter exception text.
- Command observability remains stable.
