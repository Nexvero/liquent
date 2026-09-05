# LQ-2565 Exact phase-output-name preopen gate

- Capture accepts only exact string names from the fixed phase-output mapping.
- Unsupported strings, booleans, and container values fail closed.
- Type validation precedes membership evaluation for unhashable substitutes.
- Rejection occurs before workspace opening or relative name resolution.
- Caller-selected aliases and path fragments never enter the namespace boundary.
- Existing controller phase-to-name mapping remains unchanged.
