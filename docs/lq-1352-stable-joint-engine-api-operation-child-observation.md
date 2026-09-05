# LQ-1352 Stable joint engine API operation child observation

- A dedicated helper opens each fixed child descriptor-relatively.
- It enforces real-directory, owner, private-mode, and close-on-exec facts.
- It returns one ordered tuple of complete stable metadata.
- The child descriptor closes immediately after observation.
- Initial observations use the held operation-root descriptor.
- Final observations use the re-opened visible operation root.
- Public binding values continue to expose only stable identities.
