# LQ-2513 Relist-bound replacement rejection

- Evidence injects replacement exactly while the second listing is obtained.
- The visible name, directory type, private mode, and owner remain unchanged.
- The new device and inode differ from the captured trusted identity.
- The post-relist child pass detects that mismatch and rejects immediately.
- The replacement is never adopted into controller-held state.
- Temporary-workspace cleanup remains the only consequence of rejection.
