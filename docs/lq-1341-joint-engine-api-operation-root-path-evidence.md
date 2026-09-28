# LQ-1341 Joint engine API operation root path evidence

- Tests prove a real operation-root component chain resolves.
- Tests reject a symlinked parent component.
- Tests reject a symlinked operation-root leaf.
- During-resolution disappearance and symlink rebinding are rejected.
- Same-content operation-root replacement is also rejected.
- Final traversal descriptor closure has direct evidence.
- Focused verification treats deprecation warnings as failures.
