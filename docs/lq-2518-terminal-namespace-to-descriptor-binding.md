# LQ-2518 Terminal namespace-to-descriptor binding

- Terminal verification compares each visible child with its retained descriptor.
- Both observations must independently match the captured device and inode.
- Both must remain real private directories owned by the current user.
- Same-name namespace replacement therefore differs from the held trusted object.
- Relisting and terminal binding occur without application callbacks between them.
- Receipt bytes remain unparsed until this binding succeeds.
