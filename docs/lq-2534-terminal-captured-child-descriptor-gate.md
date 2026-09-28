# LQ-2534 Terminal captured-child descriptor gate

- The held child descriptor is measured again after initial namespace lookup.
- Terminal device and inode must equal the initially captured child identity.
- Directory type, exact mode 0700, and current owner are checked again.
- Metadata drift on the held object invalidates the current capture.
- No changed terminal fact is normalized or written into controller state.
- Capture returns only after this terminal descriptor gate succeeds.
