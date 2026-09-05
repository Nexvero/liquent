# LQ-1773 Immutable joint engine API created marker result

- The created marker is an immutable result field.
- Its value is initialized only during closed construction.
- Construction exposes no created-marker argument.
- Later assignment is rejected by the result type.
- Representation continues to redact all marker detail.
- Registry and source fields remain immutable as before.
- No new public model is introduced.
