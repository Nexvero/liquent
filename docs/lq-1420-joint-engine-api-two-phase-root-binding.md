# LQ-1420 Joint engine API two-phase root binding

- Initial component traversal acquires one owner-private working root.
- Canonical encoding is followed by pre-create visible-root validation.
- Exclusive creation, write, sync, and readback use held descriptors.
- Directory sync durably publishes a successfully verified marker.
- Post-write visible-root validation closes final path continuity.
- Descriptor cleanup executes after either phase succeeds or fails.
- Existing one-shot acceptance consumes the unchanged record API.
