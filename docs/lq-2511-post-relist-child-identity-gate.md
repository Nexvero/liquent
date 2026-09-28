# LQ-2511 Post-relist child-identity gate

- Every retained child is inspected again after the stable relisting.
- The second pass repeats type, mode, owner, device, and inode checks.
- A same-name replacement during relisting therefore cannot remain invisible.
- Expected identities still originate only from controller capture.
- No replacement identity is adopted or written back into expected state.
- Any mismatch becomes the existing detail-limited controlled rejection.
