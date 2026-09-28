# LQ-1332 Final joint engine API parent rebinding gate

- The final component walker rejects newly introduced parent symlinks.
- A new real chain reaches a different leaf identity and also rejects.
- A missing parent fails before final leaf acquisition.
- No following stat call can bypass the component-level gate.
- Held source inventory is checked only against its original descriptor.
- Final path failure cannot fall back to the held detached root.
- All public source loaders share this gate.
